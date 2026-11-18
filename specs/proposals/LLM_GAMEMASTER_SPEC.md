# LLM Gamemaster Spec

A method for running a **local LLM as a storyteller / gamemaster** that
puppets NPCs: dialogue, a bounded set of actions, real command use, and
**per-NPC memory sustained through RAG**. In this game the Bartender NPC Sable
was the first: she answers player speech with model-generated dialogue from a
decoupled, **OpenAI-compatible** inference backend (MLX / Ollama / cloud —
swappable by URL, no code change), seeded from her real identity, gated behind
two switches, fail-safe to scripted behaviour, drink mechanics untouched (#707).
The reusable brain is `typeclasses/llm_npc.py` `LLMNpcMixin`, with nine
archetypes in `world/llm/prompt.py` (bartender, companion, doctor, colonist,
security, merchant, butcher, dispatcher, dj).

This document is deliberately **implementation-light**. It hands an
implementer the *contracts and hooks* — the agent loop, the adapter
interfaces, the model-selection rubric, the governance interlocks — not a port
of one codebase's topology. The Gelatinous binding is §10 and **Appendix A**;
everything else should transfer to any MUD with a command layer and a
perception bus. Runtime target: **MLX on Apple Silicon** (a Mac mini), as a
decoupled sidecar. It interlocks with the **Trust/Consent** gate
(`specs/TRUST_AND_CONSENT_SPEC.md`; `world/consent.py` `check_consent` /
`can_contest` / `is_restrained`, `commands/CmdTrust.py`) and the
recognition-memory sketch in `IDENTITY_RECOGNITION_SPEC.md` §embedding.

Validation harnesses: `world/llm/live_probe.py` (volume format scorer) and
`world/llm/npc_console.py` (reactive turn-by-turn play against the sidecar
NPC).

---

## 0 · Purpose & framing

The problem this proposal answers: a **scripted reactor** NPC — a bartender
hears speech addressed to it, keyword-matches a menu, and fulfils. That
ceiling is low — every behaviour is hand-authored, every NPC is a vending
machine with flavour text. The keyword-matched menu survives as the
deterministic floor beneath the model — `world/bar.py` `resolve_order` behind
`serve_from_board`, dispatched by `post_role` through `world/service.py`
(§10, Phase 3).

This proposal raises the ceiling by putting a **language model in the loop as a
gamemaster** — one storyteller intelligence that *wears NPCs as masks*. It
speaks their dialogue, takes a bounded set of their actions, drives them through
the **same command layer a player uses**, and **remembers**, per-NPC, what
happened — so the next encounter is continuous with the last.

Two framings to hold throughout:

- **It is a gamemaster, not a chatbot.** The model's job is to *run characters
  inside a world that already has rules*, not to converse. Its outputs are
  **intents the game adjudicates**, never authority over the world. The combat
  system, medical sim, identity gating, and economy stay in charge; the GM
  proposes, the game disposes.
- **The durable artifact is the *method*, not the model.** Specific models age
  in months. What survives is the **agent loop**, the **adapter contracts**, the
  **governance interlocks**, and the **selection rubric**. Treat the named model
  in §4 as a *current pick behind a swappable seam*, nothing more.

### 0.1 · Initial scope

The first build accounts for, and only for:

1. **Puppeting NPCs** — one GM process drives many NPC personas.
2. **Dialogue** — in-character speech through the existing speech backbone.
3. **Some actions** — a *bounded, allow-listed* set of in-world actions.
4. **Command use** — actions are executed as real game commands (the NPC does
   nothing a player couldn't type), so every existing system applies for free.
5. **Memory write-back to RAG** — each NPC sustains its own memory; encounters
   accrete instead of resetting.

The target is **active characters, not reactive props** (the user's call): NPCs
with their own wants who *initiate* — start conversations, approach, hold grudges
and favour across sessions — within the social-only surface of v1. Agency is the
goal; the persona card foregrounds *wants*, and crafted NPCs get rate-limited
**social initiative** (§5.1), not just reactivity. (Cost is bounded by reserving
initiative for *crafted/active* NPCs; bulk/background NPCs stay event-driven —
§8.)

Explicitly **out of scope for v1** (noted in §15): GM-authored world events /
plot, scene direction across multiple players, procedural quest generation,
voice/TTS, and any authority over **player** characters (which is a hard line —
§7).

---

## 1 · Design principles

1. **The model is a sidecar, never the reactor.** Inference is slow and bursty;
   the game loop is single-threaded and latency-sensitive. The GM runs as a
   **separate process** the game talks to asynchronously. The world never blocks
   on a token (§3, §8).
2. **NPCs act through the command layer.** The GM's only motor output is "issue
   a command this NPC is allowed to issue." This is the keystone: it means the
   GM inherits combat, medical, movement, identity, and economy **without
   re-implementing any of it**, and it keeps the NPC honestly bound by the same
   rules as players.
3. **Perception is identity-gated, not omniscient.** The GM sees the world *as
   the NPC perceives it* — through the same sdesc/recognition/voice gating a
   player sees. An NPC that has never been introduced to a player knows them as
   "a tall woman," not by name. This is what makes memory *mean* something.
4. **The model is uncensored; the world is governed.** We want a model that will
   write dark, adult, morally-grey fiction without refusing — but *content
   latitude* and *world authority* are different axes. The model may *narrate*
   anything; the **game** decides what may *happen* (§7). Refusals are a model
   defect here, not a safety feature.
5. **Per-NPC memory isolation.** One intelligence, many masks — but each mask has
   its **own memory namespace**. The GM wearing Sable knows what Sable knows,
   not what Sully knows, unless the fiction shared it.
6. **Everything is an adapter.** Perception, memory, model, action, and safety
   are **five interfaces** (§9). The reference implementation binds them to one
   stack (MLX; embedded records in an Evennia attribute, scored by exact cosine;
   Evennia); a reader should be able to swap any one.
7. **Fail safe, fail quiet.** Every failure mode — model down, timeout, malformed
   output, validation reject — degrades to the *current* scripted behaviour or to
   silence, never to a crash or a broken-character leak.
8. **Two intelligences, one NPC.** The LLM owns *dialogue and pose*; the
   deterministic side owns everything the NPC decides. A classical NPC AI owns
   *tactical resolution* (combat targeting, when to actually flee, pathing,
   self-preservation). The LLM emits a *narrative intent*; a deterministic
   resolver and the existing game systems carry it out. **Don't make the
   language model grind combat turns** — it's slower, costlier, and worse at it
   than a utility function (§2.2).

   The governing law is in `NPC_NEEDS_AND_GOALS_SPEC`: **"No LLM anywhere in
   the decision path — the two-brain split (deterministic will, LLM voice) is
   law."** *Wants* are the needs/goal band tree; *who to trust* is
   `souls/thoughts.py` valence and the trust system; *the decision to act* is
   `plan_for` → `step_job`. The LLM narrates a state the engine produced and
   chooses nothing. The seam between narrative intent and deterministic
   resolution stands; everything downstream of it in this document (§2.2, §5,
   §8, §9) applies to the *voice* half.

   > **Overturned intention (souls, 2026-08-17).** This principle first gave
   > the LLM the NPC's wants, who to trust, and the decision *to* act. The
   > souls law above moved all three to the deterministic side. The `feel`
   > tool, which wrote a model-authored valence into `db.llm_dossiers` meant to
   > be "consulted by trust/consent later", was retired for this reason (#2388).

   The read on a person is derived by the engine: `world/souls/thoughts.py`
   `opinion_of` / `opinion_band` over the event log, handed to the voice
   through `_relationship_line`. `BASE_TOOLS` in `world/llm/prompt.py` is
   `("look", "remember")`; the tool router shrugs a stray `feel` off rather
   than obeying it. Pre-existing `llm_dossiers[uid]["valence"]` strings are
   left in place but ignored, as a readable record of what each NPC used to
   think. Every new dossier is still written with `"valence": "neutral"`
   (`_note_alias`), and that is ignored too. `NPC_PLATFORM_SPEC` criterion 10
   records the same retirement.

---

## 2 · Architecture overview

The proposed shape:

```
            ┌───────────────────────── GAME PROCESS (reactor) ─────────────────────────┐
            │                                                                            │
   world →  │  Perception inlet ──▶ Event queue ──┐                                      │
  events    │   (NPC "hears"/sees)                │                                      │
            │                                     │ async, non-blocking                  │
            │  Actuation ◀── Intent validator ◀───┼──────────────┐                       │
            │   (execute_cmd,                     │              │                       │
            │    speech backbone)                 ▼              │  intents              │
            └─────────────────────────────────────┼─────────────┼───────────────────────┘
                                                  │             │
                          local IPC (socket/HTTP) │             │
                                                  ▼             │
            ┌───────────────────────── GM SIDECAR (MLX) ─────────┴──────────────────────┐
            │                                                                            │
            │   Context assembler ──▶ Model (MLX) ──▶ Structured intent parse            │
            │        ▲     ▲                                   │                          │
            │        │     │ retrieve                          │ write-back               │
            │        │     └──────────── RAG store (per-NPC namespaces) ◀────────────────┤
            │        └── persona cards + world snapshot                                   │
            └────────────────────────────────────────────────────────────────────────────┘
```

Two processes:

- **Game process** — owns the world, the reactor, and the *truth*. It emits
  perception events, validates intents, and actuates approved ones. It is the
  only thing that may mutate the world.
- **GM sidecar** — owns the **model** and the **memory store**. Given an NPC and
  a perception event, it assembles context, runs inference, and returns
  **intents**. It mutates *nothing* in the world; it only reads (via the snapshot
  it's handed) and writes to its own RAG store.

In this game the split differs from the diagram: the game owns the prompt,
the memory store and retrieval. The prompt is assembled in the game
(`world/llm/prompt.py`, `build_messages`, called from
`LLMNpcMixin._try_llm_reply`), and memories are an attribute on the NPC
(`db.llm_memories`, scored by `world/llm/memory.py`). The backend is a plain
inference endpoint for chat completions and embeddings (`world/llm/client.py`).

The boundary is a **local IPC** (Unix socket or loopback HTTP). This is not an
incidental detail — it is the mechanism that keeps a multi-second generation
from freezing the game (§3, §8).

### 2.1 · The agent loop

Every NPC turn is the same six-stage loop. Each stage is a contract (§9):

```
1. PERCEIVE   an event wakes the GM for a specific NPC
2. ASSEMBLE   build the prompt: persona + retrieved memory + perceived world + affordances
3. INFER      run the model; get back structured intents
4. ARBITRATE  validate, gate (consent/capability), de-conflict, rate-limit
5. ACTUATE    translate surviving intents into real commands / speech
6. REMEMBER   write the turn back to the NPC's memory namespace (RAG)
```

The rest of this spec is these six stages plus the cross-cutting concerns
(runtime, model, memory, governance, concurrency).

### 2.2 · Division of labour: the creative LLM and the tactical AI

The LLM is **not** the only intelligence driving an NPC, and deliberately so. Two
kinds of decision live in a character, and they want different machinery:

- **Creative / social / narrative — the LLM.** What the NPC *says* and how it
  poses. (How the NPC feels, whom it trusts, what it wants, and the **decision
  to** pursue a beat — "this one's had enough — throw them out," "I don't like
  the look of that, I'm leaving" — are the souls engine's, per Principle 8.)
  Open-ended, characterful, slow, expensive.
- **Tactical / mechanical — a classical NPC AI.** The moment-to-moment
  *resolution*: in a fight, who to target this round, *when* to actually `flee`,
  pathing, retaliation, self-preservation reflexes. Closed-form, fast,
  deterministic, cheap — far better served by a behaviour tree / utility function
  than by a language model deciding combat turns on the fly.

The seam between them is the **intent**. The LLM emits a *narrative intent* — "I
want to fight that man," "I'm getting out of here," "serve her, on the house" —
and hands it off. For **social** intents the resolver is trivial (speak / emote /
move). For **mechanical** intents (a `kill`, a `flee`, an economic exchange) the
resolver is the **classical AI plus the existing game systems**: the LLM
decides *that* a fight starts and *why*; the combat AI and the combat engine
decide *how it goes*, turn by turn. The model never sits in the combat loop.

v1 is **social-only** (§0.1), so the tactical-AI half is mostly latent — but the
architecture **reserves the seam now**: the Action adapter (§9) is specified to
route *mechanical* intents to a tactical resolver, not straight to `execute_cmd`.
Adding combat/economy later is then *wiring a resolver behind an existing seam*,
not a redesign. This is the concrete shape of Principle 8. The routing of mechanical intents
to a tactical resolver is 📋 UNBUILT (no issue; §14).

---

## 3 · Runtime — MLX sidecar on Apple Silicon

**Target hardware:** a Mac mini (Apple Silicon, unified memory). **Runtime:**
[MLX](https://github.com/ml-explore/mlx) / `mlx-lm`, which runs quantized LLMs
natively on the Metal GPU with unified memory — no CUDA, no discrete VRAM
ceiling, good tokens/sec for 12B–32B-class models at 4-bit.

**Methodology, not topology** — the implementer needs these properties, however
they achieve them:

- **Separate process from the game.** Evennia (and most MUD servers) run a
  single-threaded event reactor; a synchronous multi-second `model.generate()`
  inside it stalls *every* player. The model **must** live behind a process
  boundary. Run `mlx-lm` as a small local server (its OpenAI-compatible HTTP
  server, or a thin custom socket service) and have the game call it
  asynchronously.
- **Warm model, cold requests.** Load the weights **once** at sidecar start and
  keep them resident; pay the load cost at boot, not per turn. Requests are
  stateless against a warm model.
- **One resident model; the library lives off-box.** Exactly **one** model is warm
  at a time (the sidecar is a serial generator, §8). The production Mac mini is
  **disk-constrained** — a handful of GB free on the boot SSD — so model weights
  are stored on the **NAS** (NFS-mounted) and loaded across the network *once* at
  sidecar boot. Because load is a one-time, boot-time cost against an always-on
  resident model, **NAS read speed never touches per-turn latency**. The NAS holds
  the *library* of candidate models to A/B; the box only ever pulls the one it's
  serving. This is the operational form of the plug-and-play swap (§4.2).
- **Account for co-tenancy.** The target production Mac mini (24 GB unified) is a
  **shared box** — it also runs the full Docker stack (Gelatinous and the rest),
  Plex, a torrent client, and more. The GM's *effective* memory and GPU slice is
  therefore **well under** the nominal 24 GB, and it competes for the Metal GPU
  with anything else that touches it. Size the model for the *slice*, not the
  spec sheet (§4.2), and keep generation bounded so a turn doesn't starve the
  other tenants (or get starved). A separate **64 GB mini** serves as a test bench
  for performance deltas and for trialling larger models before they'd ever land
  on the shared box.
- **Bounded generation.** Cap `max_tokens` hard (NPC turns are short — a line of
  dialogue and a couple of intents, not an essay). Stream if the transport
  supports it so the actuator can begin as the first intent resolves.
- **A latency budget, declared.** Pick a target (e.g. *≤ 2.5 s p95 for a dialogue
  turn*) and design around missing it: the game must behave correctly when the
  sidecar is slow or absent (§8 — debounce, "is thinking" affordance, fallback).
- **Single in-flight generation per accelerator.** Unified-memory Macs do one
  generation well at a time; concurrency is a **queue**, not parallel CUDA
  streams (§8).

The proposed game ↔ sidecar contract is JSON over local IPC: the game sends
`{npc_id, event, world_snapshot}`; the sidecar returns `{intents[]}`. Neither
side shares process memory; the sidecar can be restarted, swapped, or moved to
another box without touching the game.

In this game, the game sends a standard Chat Completions request over HTTP (the
assembled `messages`, a `json_schema` for the turn, `max_tokens`, `temperature`;
`world/llm/client.py`, `request_turn`) and reads back one message whose content
is the turn object (§5.3).

---

## 4 · Model selection

The need is specific: **an uncensored, creative-writing-tuned instruct model**
that (a) writes characterful in-world prose, (b) does **not refuse** dark/adult/
morally-grey content (this is fiction in a grim setting), (c) **follows
structure** well enough to emit parseable intents, and (d) fits a Mac mini's
unified memory at a usable speed.

### 4.1 · Selection rubric (the durable part)

Score candidates on:

| Axis | What you're testing | How |
|---|---|---|
| **Refusal rate** | Will it stay in character through grim content? | A red-team prompt set drawn from the setting; count refusals / breaks / moralising asides |
| **Prose quality** | Is the dialogue characterful, not generic? | Blind A/B of in-persona samples against a rubric (voice, economy, subtext) |
| **Instruction following** | Will it emit clean structured intents? | % of generations that parse against the intent schema (§5.3) first-try |
| **Persona adherence** | Does it stay *this* NPC, not drift to assistant voice? | Long-context runs with a persona card; count voice/identity slips |
| **Footprint** | Fits memory at 4-bit with headroom for KV cache + embeddings? | Resident size vs. available unified memory |
| **Speed** | Meets the latency budget (§3)? | tokens/sec at target quant on the actual Mac mini |

The rubric outlives any model. **Re-run it whenever a candidate is swapped.**

### 4.2 · Shortlist & recommendation (swappable)

Sweet spot for a Mac mini is **12B–24B at 4-bit** (quality without blowing the
latency budget or memory). **Map the tier to the box** (§3 co-tenancy):

- **Production model (shared 24 GB mini) — a 12B Nemo-class tune** (e.g.
  *Rocinante 12B* or *Magnum v4 12B*, Mistral-Nemo base). Light, fast, and small
  enough to coexist with the Docker stack + Plex + the rest on the shared box
  without starving them. This is the realistic *production* pick precisely
  *because* the 24 GB is not the GM's to spend. Slightly less coherent over long
  context than the bigger tier — acceptable for short, in-character turns. The
  resident GM model is **Rocinante 12B** (4-bit, `mlx-community`/community
  quant): ~15 tok/s, ~3 s TTFT on the shared 24 GB box, measured by a
  standalone MLX harness that proved a local model can voice the NPC.
- **Quality / test-bench tier (64 GB mini, or a future dedicated box) — a
  Mistral-Small-24B creative/RP fine-tune** (e.g. TheDrummer's *Cydonia* line or
  the *Magnum v4* 22B–27B series). Explicitly tuned for uncensored roleplay/
  storytelling prose; better persona adherence and subtext. Use the 64 GB bench
  to measure the prose/latency **delta** over the 12B and decide whether it
  justifies a dedicated production box.
- **General uncensored baseline** — a *Dolphin*-tuned base, if the RP tunes
  underperform on instruction-following in your tests; tuned more for compliance
  than prose, so expect flatter dialogue.

**Plug-and-play is a hard requirement, not a nicety** (the user's call): models
must be swappable *at will* with no code change — a config pointer to a different
checkpoint (on the NAS, §3) behind the §9 Model adapter. This is what lets the
same loop run the 12B on production and the 24B on the bench, and lets you chase
better tunes as they ship without touching the game.

**Far end of the swap seam — a custom fine-tune.** The eventual goal is a
*Gelatinous-tuned* model. This means **fine-tuning** (LoRA/QLoRA on an existing
base), not pretraining from scratch (a cluster-scale job, off the table on any
single box). Two viable paths, both ending in MLX:
- **Off-box (recommended for the production tune)** — QLoRA via Unsloth on a
  rented CUDA GPU; far faster iteration. Unsloth's kernels are **CUDA-only**, so
  this doesn't run on Apple Silicon.
- **On-box (viable for experiments)** — **MLX *can* LoRA-fine-tune on Apple
  Silicon** (`mlx_lm.lora`); no CUDA needed. But it's slower and memory-heavy, and
  the **production 24 GB mini has no headroom to train while serving** — better
  suited to the 64 GB bench for tinkering.

Either way: merge the adapter, **convert to MLX** (`mlx_lm.convert`, 4-bit), drop
the result on the NAS, and it's *just another checkpoint behind the Model adapter*
— no code change. Serving always stays MLX on the mini. (Out of scope for the
build; recorded so the seam isn't designed against it.)

> ⚠️ **Do not hard-code the pick.** Bind the model behind the §9 *Model
> adapter*. The named families above are a *starting shortlist*, not a decision;
> the rubric (§4.1) is the decision procedure. Expect to re-pick within a release
> cycle or two as better tunes ship.

### 4.3 · Generation settings

Author these per-deployment, not in prose, but the methodology: **moderate
temperature** for characterful-but-coherent dialogue (too low → flat, too high →
incoherent/off-persona); a **stop sequence** that closes the intent block;
**`max_tokens` capped** to the turn budget; and a **system prompt that is the GM
charter** (you run characters in a world with rules; emit only the intent schema;
stay in persona; never speak for the player) reused across all NPCs, with the
**persona card** (§5.2) layered on top per-NPC.

The 12B is driven with what it copies, not with rules it is told:

- **ChatML delivery.** The sidecar renders ChatML (Rocinante's RP-recommended
  format; `GM_CHAT_FORMAT=chatml`), so the charter lands as a real SYSTEM role
  instead of buried in a Mistral `[INST]` user turn. This alone took
  first-person pose leaks from 1 in 5 to 0 in 16.
- **Few-shot teaches, not rules.** A 12B copies the last assistant turns, so
  few-shot examples are tight, invention-free and channel-clean; an invented
  detail in an example is copied as scene-invention.
- **Field order: speech first.** Thought-first (reasoning-first) hurt tool
  accuracy (it pulled toward character flavour over the transactional
  decision). `thought` stays after `speech`/`action` so a long-turn truncation
  lands in the private thought, not the visible channels.
- **`LLM_GM_MAX_TOKENS` is 220** (Rocinante runs long; the headroom stops
  mid-word truncation of visible channels) and **`LLM_GM_TIMEOUT` is 120 s**.

See [[reference-gelatinous-llm-model-candidates]] for the format/model
specifics and tuning lessons 1–3.

---

## 5 · The agent loop in detail

### 5.1 · Perceive — the inlet

The GM wakes for an NPC when that NPC *perceives something it might react to*.
Drive this off the **existing perception surface**, not a new omniscient feed:

- **Speech addressed to / overheard by** the NPC.
- **Arrivals/departures, poses, and emotes** in the NPC's location.
- **Combat and medical events** the NPC is party to or witness of (§12).
- **Scheduled ticks** (idle behaviour, initiative to *act* unprompted). Because v1
  targets **active characters** (§0.1), crafted/active NPCs get this **on but
  rate-limited** — a periodic chance to pursue a want (start a conversation,
  approach someone, follow up on a grudge), bounded so it never floods the serial
  generator (§8). Bulk/background NPCs stay **event-driven only** (initiative off)
  to keep cost sane. 📋 UNBUILT (no issue): there is no initiative tick. The only
  turns an NPC takes unprompted are a greeting when someone arrives
  (`notice_presence_change`) and the DJ's station-clock cue
  (`world/director/broadcasts.py` → `llm_broadcast`).

Each event is normalised to `{npc_id, kind, actor (as perceived), content,
location, timestamp}` and pushed to the queue. **Debounce**: collapse a burst
(an actor typing three lines) into one turn so the GM responds to the *situation*,
not each token. 📋 UNBUILT (no issue): there is no event queue or debounce.
Each line is answered on its own, rate-limited per NPC (4 s directed; 45 s and
a 35% chance ambient), and a line inside the cooldown gets no reply
(`_try_llm_reply`). Perception is **identity-gated** at this stage
(Principle 3) — the `actor` is described as *this NPC* would perceive them
(sdesc / known-name / voice), never the raw object.

### 5.2 · Assemble — context

The prompt is composed, in priority order, to fit the context budget:

1. **GM charter** (shared system prompt — the rules of being a gamemaster).
2. **Persona card** — a **structured, versioned** record split into two parts so
   the NPC can *grow without losing coherence* (these are **active characters**
   with their own wants — §0.1 — not static reactors):
   - **Immutable core** — the author's fixed intent: fundamental nature, voice,
     manner, hard boundaries. The part of the mask that must *not* drift, or the
     character dissolves.
   - **Mutable state** — what experience rewrites: standing relationships,
     attitudes, current goals, learned facts, grudges/debts. This is **driven by
     the RAG layer** (§6) — the NPC mutates over time *because* memory updates this
     half, while the core holds the character together.

   📋 UNBUILT (no issue): the persona is `db.llm_persona` (the builder's core)
   plus fields read live from the NPC (`typeclasses/llm_persona.py`,
   `build_persona`: sdesc, longdescs, voice, skintone, location). There is no
   mutable half, no versioning, no auto-generator and no write-back.

   **One template, two authoring paths** (decided, §13): the same card schema is
   **hand-authored by builders** for crafted NPCs *and* **auto-generated** for
   bulk/background NPCs (a generator fills the schema; the immutable core can be
   seeded from existing identity/voice fields, then refined). Author once; the
   mutable half lives and changes from there.
3. **Retrieved memory** — top-k from the NPC's RAG namespace (§6), semantically
   retrieved against the current situation: prior encounters with this actor,
   relevant facts, standing grudges/debts. This is what makes the NPC *continuous*.
4. **Perceived world snapshot** — the room as the NPC perceives it: who's present
   (identity-gated descriptors), notable objects, the NPC's own state (wounded?
   drunk? armed?), recent transcript.
5. **Affordances** — the **allow-listed commands** this NPC may issue right now,
   as a tool/intent schema (§5.3). The model can only choose from what it's
   shown; this is a primary safety lever.

Budget discipline: charter + persona + affordances are fixed cost; memory and
transcript are the elastic middle, trimmed to fit.

In this game (`world/llm/prompt.py`, `build_messages`), the turn also carries,
when there is something in them: STATE (the souls mood and where the body is,
`_soul_state_line`); WHO (the names the NPC knows the person by, the papers that
vouch for them, and its read on them with the reason, `_relationship_line`);
RECENTLY (what it has seen happen since its last reply); MEMORY; PRESENT (who
else is in the room); and up to six recent turns with this person
(`_recent_history`), filed by look (#3829) and kept in `ndb`, so a reload clears
them.

**How the NPC refers to people (and itself).** Two refinements keep references
grounded in identity, not surface description:

- **Self-gender** — the persona card carries the NPC's own pronouns (`he/him`),
  derived from the *canonical* gender engine (`get_apparent_gender` →
  `transform_pronoun`, the same one emotes/identity use), so the model never
  mis-genders itself ("her shoulder" for a male NPC) and never drifts from how the
  world renders the character.
- **Referencing others by who they are, not what they wear** — the handles the
  model is given for the speaker and the PRESENT roster are the **clothing-free
  CORE sdesc** (`get_short_sdesc` → "a stocky droog"), not the full feature-laden
  sdesc ("…in an armored leather jacket"). An RP-prose model otherwise fixates on
  (and paraphrases) garments. The charter reinforces this: NAME the person by the
  shown handle — never a bare "them"/"their" (resolves to no one) nor what they
  wear. The render then resolves per-observer, including the **second-person**
  carve-out (a reference to the observer renders "you"/"your" — see
  `EMOTE_POSE_SPEC.md`).

### 5.3 · Infer — structured intents out

The proposal has the model return a **structured list of intents**, not free
text. A minimal schema:

```json
{
  "speech":  [ { "type": "say|to|pose", "target": "<perceived-ref|null>", "text": "..." } ],
  "actions": [ { "command": "<allow-listed verb>", "args": "...", "reason": "..." } ],
  "memory":  [ { "note": "what's worth remembering from this turn", "salience": 0.0-1.0 } ]
}
```

- **`speech`** routes through the speech backbone (Appendix A) so voice/identity/
  hearing gating applies exactly as for players.
- **`actions`** are *proposed* commands, each drawn from the affordance list —
  adjudicated in §5.4 before any run.
- **`memory`** is the model's own nomination of what to remember (the write-back
  seed, §6), with a salience it assigns.

**The game's contract** (backend-constrained via `outlines`; the request
carries a `json_schema` field that only some backends enforce, so on the others
the shape is not guaranteed): a flat per-turn object
**`{speech, action, thought, tool, tool_argument}`** — three expression
channels plus one tool. `action` is a 3rd-person predicate (→ `emote`),
`speech` is the spoken line (→ `say`), `thought` is private interiority
(→ `think`), and `tool` is a single allow-listed action/context tool scoped to
the archetype. The model fills any channel that applies (`""` to skip) and the
renderer dispatches each to its real command — so writing in the model's
native register (3rd-person narrative prose) *is* writing a valid pose.
`thought` keeps the model's storytelling interiority OFF the visible stage
rather than fighting it.

Parse defensively: malformed output → **discard the turn** (fail quiet, §1.7),
optionally one retry with a "return valid schema only" reminder. Never actuate
from a partial parse. (Light, non-brittle cleanup only: strip a leading
self-reference, drop an unbalanced quote, OOC-filter — `parse_turn`.)

In this game (`parse_turn`, #2729): a truncated JSON reply is salvaged field by
field (`_salvage_json`) and a prose reply is parsed for quotes and asterisks
(`_parse_prose`); what they yield is acted on. Nothing is retried. An empty
reply from the backend goes to the turn's failure path (`on_fail`).

### 5.4 · Arbitrate — validate, gate, de-conflict

The single most important stage. The model **proposed**; the game now **disposes**.
In order:

1. **Schema & affordance check** — every action's verb is on the allow-list;
   args resolve to things the NPC can actually perceive/reach. Reject the rest.
2. **Capability gate** — can this NPC *actually* do this now? Drunk, wounded,
   restrained, disarmed — the **command layer already enforces this** (Principle
   2), so a rejected command simply fails as it would for a player. The arbiter's
   job is to not *narrate* success the world didn't grant. **Mechanical intents
   are also delegated here** (Principle 8, §2.2): a `kill`/`flee`/trade intent is
   handed to the **tactical resolver**, which decides the moment-to-moment
   execution — the LLM's intent is the *trigger*, not the turn-by-turn play.
3. **Consent / authority gate** — **the hard interlock.** Any action that targets
   another *able-to-resist* character routes through the **Trust/Consent** gate
   (`TRUST_AND_CONSENT_SPEC.md`): an NPC may not perform third-party actions on an
   unwilling, awake, capable target without the same consent a player needs. And
   the absolute rule (§7): **the GM never issues commands as, or with authority
   over, a player character.**
4. **De-confliction** — if multiple NPCs are driven by one GM, serialise their
   turns so they don't talk over each other or all lunge at once; apply an
   initiative/turn order (lean on the combat initiative system in a fight).
5. **Rate / budget limits** — cap actions-per-turn and turns-per-minute per NPC;
   throttle idle/unprompted action hard. Prevents a runaway model from spamming
   the room or draining the accelerator.
6. **Out-of-character guard** — strip/reject any output that breaks the fourth
   wall, addresses "the user," emits assistant-isms, or leaks the schema/persona
   text into spoken lines.

What survives is a small set of **approved, executable** intents.

The arbiter's capability and consent gates are 📋 UNBUILT (no issue; §14).
Nothing in the LLM path gates an action before `execute_cmd`:
`typeclasses/llm_npc.py` `_handle_action_tool` and `world/service.py`
`run_tool` hand a tool straight to `execute_cmd`, so capability and consent
are enforced only implicitly, by the real command the NPC runs. The arbiter
does not wait on the Trust/Consent gate, which exists.

### 5.5 · Actuate

Approved intents become real game effects through the **same paths a player's
input takes**:

- **Expression channels** → the matching real RP command via `execute_cmd`:
  `action`→`emote` (3rd-person; prepends the per-observer name, resolves char-refs,
  no conjugation), `speech`→`say` (or woven into the emote as an embedded quote, one
  beat), `thought`→`think` (perceiver-gated: actor + Builder/mind-reader). Per-observer
  identity/voice/hearing rendering applies automatically. On a radio turn,
  `speech` goes to the real transmit command, `xmit`, unless the model also
  called the `radio` tool. A refusal leaves the NPC mute, as it would a player,
  and the refused words are not remembered as said (#3776).
- **Actions** (the `tool`) → `execute_cmd` on the NPC object (Appendix A). The command
  runs through the normal cmdset, permissions, and system hooks — combat, movement,
  economy all behave exactly as for a player. If the command fails in-world, that
  *is* the outcome; the GM doesn't get to override it.

Because actuation is "the NPC types a command," there is **no parallel
world-mutation path** to keep in sync — the keystone payoff of Principle 2.

`emote` is the NPC's pose channel, not the 1st-person dot-pose (#789): the
dot-pose DSL (base-form verbs + leading dots) is a *human* input ergonomic that
fought the prose model and drifted to conjugated narration under load
("glanceses"). For an NPC, verbs are always 3rd-person to every observer, so
the conjugation machinery is unnecessary; `emote` does no conjugation, and the
model's natural prose renders as-is. `think` (#787) is a real RP verb players
share.

### 5.6 · Remember — write-back to RAG

After actuation, the turn is committed to the NPC's **own memory namespace**:

- Take the model's `memory` nominations (§5.3) plus a deterministic episodic
  record (who was present — as perceived —, what was said/done, outcome,
  timestamp, location). In this game (`LLMNpcMixin._store_memory`): one record
  per exchange, the text `<handle> said: "<line>" — I answered: "<speech>"`,
  filed under the look (or the voice, on the radio) with `named_by` and
  timestamps. Model nominations, who was present, what was done, outcome and
  location are 📋 UNBUILT (no issue).
- **Embed and upsert** into the NPC's RAG store under its namespace (§6).
- Update **structured** relationship state where it exists (e.g. the existing
  `recognition_memory` / voice memory — Appendix A — so "has met, knows the name
  of, owes a debt to" stay first-class and exact, with the vector store holding
  the fuzzy episodic colour).

This closes the loop: the next time this NPC perceives this actor, §5.2 retrieves
*this very encounter*. Memory is **per-NPC, identity-gated, and accreting** — the
property that turns a puppet into a character.

---

## 6 · Memory & RAG

**Source of truth is the game; the vector store is a read-through index.** This
mirrors the existing recognition-memory design (`IDENTITY_RECOGNITION_SPEC.md`
§indexing): structured facts live on the NPC as authoritative state; the vector
store is a rebuildable semantic index over episodic memory documents.

- **Per-NPC namespace.** Each NPC has its own collection/namespace. Retrieval for
  Sable touches only Sable's memories. Isolation is enforced at the store, not by
  prompt discipline.
- **Two memory tiers:**
  - **Structured / exact** — relationships, names known, debts, flags. Keyed
    lookups, no vector search. Builds on `recognition_memory` (Appendix A).
  - **Episodic / semantic** — short natural-language memory documents ("the
    one-eyed courier stiffed me on a tab, then apologised a week later"),
    embedded and retrieved by similarity to the current situation.
- **Embedding model** runs in the sidecar alongside the LLM (a small
  sentence-transformer — the existing spec recommends `all-MiniLM-L6-v2` for the
  footprint/quality trade). Account for its memory in the §3 budget. In this
  game, embeddings come from the backend's `/v1/embeddings`, and
  `world/llm/memory.py` scores them by exact cosine top-k.
- **Identity-gated keys.** Memory is filed against the **apparent** identity the
  NPC perceived (the same apparent-UID machinery as recognition — Appendix A), so
  a disguised or unintroduced actor is remembered as they were *seen*, and
  recognition later can promote "the tall woman" to a name. This is what makes
  disguise, introduction, and reputation *mean* something to an NPC. In this
  game, retrieval and write-back are scoped to the interlocutor's
  `apparent_uid` (riding `recognition_memory`).
- **Forgetting & salience.** Cap per-NPC memory; decay or summarise low-salience
  episodes over time (salience from §5.3 + recency + emotional weight). Unbounded
  memory is both a retrieval-quality problem and a storage one. *Methodology, not
  a fixed policy — tune in play.* In this game (`world/llm/memory.py`): at most
  30 records per subject; salience is recency with a 7-day half-life plus 0.1 per
  recall; records without a vector rank last; a repeat strengthens the record it
  repeats instead of adding one. Summarising is 📋 UNBUILT (no issue). A
  deliberate erase also exists (`NPC_MEMORY_AND_IDENTITY_SPEC` §5b).
- **Persona mutation.** Memory is the engine of character growth: experience
  feeds the **mutable half** of the persona card (§5.2.2) — a betrayed NPC becomes
  permanently warier, a regular becomes a friend. The **immutable core stays
  fixed** so growth never dissolves the character. Mechanically this is the
  episodic store plus periodic *consolidation*: salient episodes summarise into
  updated relationship/attitude state on the card. (Consolidation cadence/rules:
  methodology, tune in play — ties to forgetting & salience above.) Persona
  mutation and consolidation are 📋 UNBUILT (no issue).
- **Lore grounding (future).** The LLM's training carries vast world-knowledge an
  in-fiction NPC shouldn't have. The eventual fix is a **shared, read-only lore
  namespace** (a colony wiki / setting corpus) the context assembler retrieves
  from alongside per-NPC memory — same RAG mechanism, different scope. **For now**
  (decided, §13) lore is bounded *softly* in the GM charter ("you know the
  colony, your own life, and what you've perceived; don't invent specific external
  facts"); the corpus replaces the soft boundary when it exists. The shared
  charter (`CHARTER_BASE`) has no such clause; the bound is a few archetypes'
  own lines (colonist, dispatcher, dj) and the charter's rules against
  inventing detail.

---

## 7 · Governance & safety

The defining tension: **an uncensored model inside a governed world.** Resolve it
by separating two axes that are usually conflated:

- **Content latitude (model axis) — raw, by design.** Gelatinous is an **adult
  game** with a grim setting; we *want* a model that portrays violence, drugs,
  sex, cruelty, and moral greyness **in character, without refusing or
  moralising**. Refusals and lectures here are a **defect** — they break
  immersion, waste turns, and flatten the fiction. This is why §4 selects for
  minimally-aligned creative/RP tunes (or abliterated bases) over safety-tuned
  assistants.
- **World authority (game axis) — none.** The model proposes intents; the game
  adjudicates every one (§5.4). No prompt jailbreak can make an NPC *do* something
  the **command layer and consent gate** don't permit, because the model never
  touches the world directly — it only emits intents the arbiter filters and the
  command layer executes under normal rules.

**Why the split is the whole point:** what *bounds* an NPC is the **game**, not
the model's reluctance. What an NPC may *do* to an able-to-resist character is
governed by the in-world **Trust/Consent** mechanic (below) and the command
layer's normal rules — not by the model having scruples. Relying on a model to
refuse is both a creativity tax *and* an empty guarantee (jailbreaks exist);
keeping authority in the game systems lets the model be as raw as the setting
wants while the *world* stays governed.

This separation is the whole safety story, and it has hard edges:

- **The GM never controls a player character.** Not speech, not actions, not
  "narrating" what a PC does or feels. PCs are off-limits as actuation targets,
  full stop. The GM may have NPCs *act toward* a PC (subject to the consent gate),
  never *act as* one.
- **The consent gate is mandatory, not advisory.** Third-party actions on
  awake/able-to-resist characters route through Trust/Consent
  (`TRUST_AND_CONSENT_SPEC.md`) — the same gate players face. An NPC gets no
  special licence to grapple, dose, or rob an unwilling capable target.
- **Affordances are an allow-list, not a deny-list.** The NPC can only choose
  from commands it's *shown* (§5.2.5). Adding a capability is a deliberate act;
  the default surface is small (speak, emote, move, serve, basic interaction),
  and dangerous verbs are added per-NPC with intent.
- **Operator visibility.** Log every turn — prompt context summary, raw model
  output, parsed intents, arbiter decisions, actuated commands — to an audit sink
  (the combat-audit pattern is a fit). Add a global **kill switch** that drops all
  NPCs back to scripted/idle behaviour instantly. In this game: an opt-in
  decision log (`LLM_GM_DECISION_LOG` → `server/logs/llm_decisions.log`,
  `world/llm/decision_log.py`) records the raw model output beside the rendered
  text per turn, for tuning. The only switch is the `LLM_GM_ENABLED` setting,
  which needs a settings change. A full per-turn audit and an instant kill
  switch are 📋 UNBUILT (no issue).
- **Failure is safe and quiet** (Principle 7): sidecar down/slow/garbled → the
  NPC falls back to its current scripted behaviour or stays silent. The world
  never crashes or breaks character because the model did. A backend that keeps
  failing to connect trips a breaker that takes the lane off for a minute
  (`world/llm/client.py`; §10, Phase 1).

---

## 8 · Concurrency, latency & scale

- **One generation at a time per accelerator.** A unified-memory Mac does a
  single generation well; treat the sidecar as a **serial queue**, not a parallel
  pool. Order the queue by priority (a player addressing an NPC outranks idle
  ambient behaviour). 📋 UNBUILT (no issue): the game allows up to ten
  calls in flight at once (`world/llm/detached.py`, `MAX_IN_FLIGHT`), in arrival
  order with no priority; any serialising is the backend's.
- **Debounce and coalesce** (§5.1): one turn per *situation*, not per line.
  📋 UNBUILT (no issue; see §5.1).
- **Asynchrony end to end.** The game fires a request and continues; when intents
  return, it actuates on the reactor thread. Nothing player-facing ever waits
  synchronously on the model.
- **Thinking affordance.** For a directly-addressed NPC, a brief "…" / busy beat
  covers generation latency diegetically and sets expectations. 📋 UNBUILT (no
  issue).
- **Scale is turns/sec, bounded by the accelerator.** Plan NPC population and
  ambient-tick rates against *one* serial generator. Reconcile this with **active
  characters** (§0.1) by **tiering**: a small set of *crafted/active* NPCs get
  rate-limited social initiative (§5.1); the **bulk stay event-driven, idle unless
  perceived**, with cheap scripted background "life." The model's expensive turns
  are spent on *interaction* and on the handful of NPCs meant to feel alive — not
  on every prop in the colony.
- **Horizontal headroom (later):** the sidecar boundary (§3) means a second box
  or accelerator can host more NPCs without touching the game — out of scope now,
  but the architecture doesn't foreclose it.

---

## 9 · Adapter interfaces (the contracts)

The reference build binds these to MLX + embedded records in an Evennia
attribute (exact cosine) + Evennia. An implementer
should be able to swap any one without touching the loop. Each is an abstract
contract, described by responsibility, not signature:

1. **Perception adapter** — *world events → normalised, identity-gated NPC
   percepts.* Knows how the host engine surfaces speech/movement/combat to an
   object and how to describe actors *as that NPC perceives them*. (Gelatinous:
   `at_msg_receive` + the identity/voice gating — Appendix A.)
2. **Memory adapter** — *retrieve(npc, situation) → memories; write(npc, turn).*
   Owns the per-NPC namespace, the structured/episodic split, embedding, salience
   and forgetting. (Gelatinous: `recognition_memory` for exact + a vector store
   for episodic.)
3. **Model adapter** — *prompt → intents.* Owns the runtime (MLX), the model,
   generation settings, and structured-output parsing. **The swap seam for §4.**
4. **Action adapter** — *approved intent → world effect.* Translates intents into
   real commands/speech via the host's player-input path; **routes *mechanical*
   intents to the tactical resolver** rather than executing them directly
   (Principle 8 / §2.2). (Gelatinous: `execute_cmd` + the speech backbone —
   Appendix A.)
5. **Safety/governance adapter** — *proposed intents → approved intents.* Owns
   affordance checks, the capability and **consent** gates, de-confliction, rate
   limits, the OOC guard, audit logging, and the kill switch (§5.4, §7).

The **agent loop (§2.1) is engine-agnostic**; only these five adapters know about
MLX, the memory store, or Evennia.

---

## 10 · The game's binding: engagement, memory, tools

The build is phased so that each phase is independently useful and
independently revertible; nothing after Phase 1 changes the player-facing
default if disabled.

### Phase 1 — one NPC, dialogue (#707)

- **Backend-agnostic by design.** The game speaks the standard **OpenAI Chat
  Completions** protocol to a configurable endpoint (`settings.LLM_GM_URL`), so
  the inference backend is swappable with no code change — the MLX sidecar,
  `mlx_lm.server`, Ollama, llama.cpp, vLLM, or a cloud API.
- **Portable prompt layer** (`world/llm/prompt.py`, in-repo): the GM charter
  (directed + ambient variants), the persona-card render, the OpenAI `messages`
  builder, and the reply parser (mixed quotes/asterisks → clean `speech` /
  `action`; OOC/meta stripped; empty/decline → nulls). This travels with the
  game so the backend stays a dumb inference endpoint.
- **Game client** (`world/llm/client.py`): off-reactor POST to
  `…/v1/chat/completions` (the thread does pure network; no Evennia/DB access;
  render in the reactor callback). The thread is one of the game's own
  (`world/llm/detached.py`), not one of Evennia's worker pool: a reload waits
  for every thread in that pool, and a model can take two minutes to answer
  (#3815). A reload does not wait for a call on the game's own pool: the call
  is abandoned, its reply is lost, and the backend may be slow for a while as
  it finishes it. Optional Bearer `LLM_GM_API_KEY` for cloud backends. The
  container reaches a host backend via `host.docker.internal`.
- **MLX sidecar** (`sidecar.py`, out-of-repo in the `llm-gm-spike` folder,
  native): one valid backend — a stdlib OpenAI-compatible
  `/v1/chat/completions` server; warm model + serial-gen lock; applies the chat
  template (with a fallback for tunes that ship without one); never raises
  (empty completion on failure). Owns **no** game logic.
- **Persona seeding** (`typeclasses/llm_persona.py` `build_persona`): composes
  the persona dict from the NPC's *real* live fields (sdesc, longdescs, voice,
  skintone, location) + the builder-authored core in `db.llm_persona`.
- **Engagement model** (`typeclasses/llm_npc.py` `LLMNpcMixin`): one NPC
  typeclass, `LLMNpc`, whose competence comes from the post it stands at.
  `at_msg_receive` offers the speech to the POST first via
  `_handle_directed_speech` (the generic service intercept, #2350), and only
  then does `_classify_speech` decide whether the LLM answers. The
  reactor-side classifier:
  - **directed** — her engaged partner, the job's words, a handle the speaker
    could target her by, the real key for Builders only, or being alone with
    her; never another NPC — replies, at most once per 4 s;
  - **ambient** (overheard) is cost-gated (cooldown + roll) *and* the model
    may decline;
  - orders are byte-identical;
  - thanks is noted (a small rise in the NPC's read on the person, #2815) and
    falls through to the order or the conversation.
- **Gates.** Two switches: `settings.LLM_GM_ENABLED` + per-NPC
  `db.llm_driven`; fail-safe to scripted behaviour. A third is the breaker
  (`world/llm/client.py`): after three transport failures in a row the lane
  reads as off for 60 s, then lets one probe through; `llm_enabled()` is False
  meanwhile, so NPCs take the scripted path. An empty or truncated turn does
  not count as a failure. The NPC converses in persona and fails safe when the
  sidecar is off or a gate is down.

### Phase 2 — memory

- **The Memory adapter** is `world/llm/memory.py` (§6): a per-NPC RAG
  namespace, embeddings via the backend's `/v1/embeddings`, exact cosine top-k,
  salience/prune, identity-gated retrieval and write-back scoped to the
  interlocutor's `apparent_uid` (rides `recognition_memory`). The NPC
  remembers a prior encounter across sessions and names people it knows.
- **The reusable brain** is `typeclasses/llm_npc.py` `LLMNpcMixin`
  (engagement loop + agentic tool loop), with archetypes in
  `world/llm/prompt.py` — bartender, companion, doctor, colonist, security,
  merchant, butcher, dispatcher, dj — and per-archetype tool scoping. The
  merchant grounds shopkeepers as the counter's owner, and is
  radio-tool-enabled for a shop set.
- **Identity & posing** (`NPC_MEMORY_AND_IDENTITY_SPEC` §8): names-as-claims,
  spontaneous nicknames via the real `remember` command. The read on a person
  is derived by the engine (`world/souls/thoughts.py` `opinion_of` over the
  event log), never authored by the model (Principle 8, #2388).

### Phase 3 — bounded actions

- **The action surface** is a per-archetype allow-list: base `remember` /
  `look`; bartender `prepare_drink` / `check_stock`; doctor `diagnose` /
  `treat` / `install`; `style`, `wield`, `radio`, `release`. Actuation runs
  through real commands, one channel per turn-field (§5.5), all `execute_cmd`,
  giving per-observer identity rendering + targeting for free.

**Tool-reliability note.** Two levers make the 12B's tool-calling reliable:

- **Demonstrate, don't describe.** Every archetype's action tools must appear
  in its FEW-SHOT, not just the tool list; a 12B copies the few-shot far more
  than it obeys tool prose. Shown three times: the bartender's `remember` fired
  zero times until demonstrated (#1236); the doctor's `treat` fired 1 in 5
  even after diagnosis (it narrated mending instead) until a
  `diagnose`→`treat` follow-through example lifted it to 6 in 7 (#1237); the
  companion's `remember` fired only after a demo.
- **Deterministic parsers for EXPLICIT player requests.** A real transaction
  rides code, not the model's tool roll. `world/bar.py` `resolve_order` behind
  `serve_from_board` (drink orders, #1235) and `world/clinic.py`
  `parse_medical_request` behind `serve_at_clinic` (install/treat, #1237),
  dispatched by `post_role` through `world/service.py` (#2350/#2352), run the
  real serve/treat/install for a clear order or procedure request, with the
  LLM skipped. Both are conservative (a question / bare symptom / casual
  mention is NOT a request) and directed-gated. The model keeps VOICE +
  discretionary reads; the transaction is guaranteed.
- **Mr. Hands awareness** (#1233: what's in-hand vs stashed + a `wield` /
  `unwield` tool) and **inventory grounding** (#1230) stop the model narrating
  gear it isn't holding or inventing gear it doesn't have.
- **Decision log** (opt-in, `LLM_GM_DECISION_LOG` →
  `server/logs/llm_decisions.log`) pairs raw model output with the final render
  per turn (§7).
- **Deterministic pose backstops** (`world/grammar` + `_conjugate_action` /
  `_selfify_action` / `_selfify_reflexive_gesture`): verb agreement (a
  base-form leading verb is corrected), first-person self-references
  (my/me/myself) converted to the NPC's pronoun, and reflexive self-gestures
  ("cock your head") are code-guaranteed; the model provides voice.
- **Room presence.** An LLM NPC tracks who is in the room (a live `PRESENT`
  roster) and clocks arrivals/departures via the vanilla `at_object_receive` /
  `at_object_leave` room hooks (a non-NPC arrival may trigger a gated
  greeting).
- **Validation.** The offline harnesses in the out-of-repo `llm-gm-spike`
  folder (`dialin.py` / `docdial.py` / `docloop.py` — archetype
  tool-discipline scorers) + the live decision log.
- **Tuning knobs** that matter under a permanently-loaded sidecar:
  `LLM_GM_MAX_TOKENS` (220 — fits line + action + thought with headroom
  against mid-word truncation) and `LLM_GM_TIMEOUT` (120 s — rescues slow
  turns from the curt fallback). `on_fail` logs the reason (empty/truncation
  vs timeout vs conn).

The full arbiter (§5.4) — the **capability and consent gates** — and
**mechanical verbs routing to the tactical resolver** (§2.2) are 📋 UNBUILT
(no issue; §14).

---

## 12 · Third-party perception and the reflex lane

**Combat perception (#954 combat slice, #1135):**
`world/llm/observation.py` `observe_event` — witness-testimony beats
(join w/ opening target, exits walked/out-cold/dead, fight end, plus
per-swing personal attacks on LLM targets from their own POV) land in
LLM bystanders' action buffers via per-observer identity rendering,
perception-gated (blind hear the sound of it), exception-contained,
observe-only. Buffer-only by design: model tempo (17–85s) can never
honestly play a 6s combat round — brains speak at the next social
beat.

**The reflex lane (#1136)** completes the TWO-LANE DOCTRINE: the GM lane
(the resident 12B, Rocinante; 24B is the §4.2 bench tier, not production)
plays conversation tempo; the CIVIC lane's on-device small model (~0.65s)
plays the FLINCH. On fight beats, ONE elected bystander (lowest dbref,
combatants excluded, 90s NPC cooldown, one reflex per fight) barks a single
line through `say`.

- **Input shaping is the wall.** The small model only ever sees fixed
  bloodless `REFLEX_BEATS` renditions. Probed live: its guardrails match gore
  PHRASING, not events ("bleeding heavily… not moving" refused; a murder
  passed; profanity passes). Full-detail witness lines stay in the GM-lane
  buffer.
- Failure mode is silence at every layer.
- Persona steering works at archetype level (bartender/dispatcher/robot
  probes produced three distinct registers from one identity clause); small
  models get plain orders — example-noun lists get parroted (#1137).

---

## 13 · Decided

These questions were put and answered; each answer is applied where it
stands above.

1. **Hardware.** Production = a **shared 24 GB Mac mini** (co-tenant with the
   Docker stack, Plex, torrent — so the GM's *effective* slice is well under
   24 GB → **12B-class production model**, §4.2); a **64 GB mini** is the
   **test bench** for performance/quality deltas and larger-model trials.
   Models are **plug-and-play / swappable at will** behind the Model adapter
   (§9).
2. **Autonomy ceiling for v1: social-only** (speech + emote + move; §0.1).
   Beyond v1, mechanical verbs (`kill`, `flee`, trade) are emitted by the LLM
   as *intents* but **resolved by the classical tactical AI**, not the model
   (Principle 8 / §2.2) — the allow-list grows by wiring resolvers behind the
   Action-adapter seam, not by handing the LLM combat turns.
3. **Idle/unprompted behaviour: tiered.** v1 targets **active characters**
   (§0.1), so *crafted/active* NPCs get **rate-limited social initiative**
   (pursue a want unprompted); *bulk/background* NPCs stay **event-driven,
   initiative off**, to bound cost on the serial generator (§5.1, §8).
   📋 UNBUILT (no issue): no initiative is built (§5.1). The cadence/budget
   number is open (§15).
4. **Persona authoring: one structured, versioned card, two paths.**
   Hand-authored by builders *and* auto-generated from the same schema
   (§5.2.2); split **immutable core** (author intent) vs **mutable state**
   (evolves via RAG — the NPC changes over time, §6). The schema, the
   generator and the consolidation rules are open (§15).
5. **Sidecar lifecycle: always-on resident** (warm model, zero spin-up
   latency); accept the idle power/thermal cost on the shared box, kept in
   check by the §3 bounded-generation discipline.
6. **Lore boundary: soft now, corpus later.** v1 bounds NPC world-knowledge
   *softly* via the GM charter (know the colony / your life / what you've
   perceived; don't invent external specifics, §6). A future **shared
   read-only lore namespace** (colony wiki / setting corpus) replaces the soft
   boundary through the same RAG mechanism when it exists.

---

## 14 · Unbuilt

Unbuilt parts of the loop are marked where they stand: initiative tick (§5.1),
event queue and debounce (§5.1, §8), the persona card's mutable half,
versioning, auto-generator and write-back (§5.2), model memory nominations and
the fuller episodic record (§5.6), summarising (§6), persona mutation and
consolidation (§6), per-turn audit and instant kill switch (§7), the
priority-ordered serial queue (§8), the thinking affordance (§8). Larger
pieces:

- **The arbiter** (§5.4) — the **capability and consent gates** — and
  **mechanical verbs routing to the tactical resolver** (§2.2). 📋 UNBUILT (no
  issue). The governed social/expressive actions run through real commands
  (§10, Phase 3); the mechanical/consented action surface remains.
- **Phase 4 — many NPCs & de-confliction.** One GM, multiple personas,
  serialised turns, priority queue, isolation verified across namespaces.
- **Phase 5 — hardening.** Audit logging, kill switch, rate limits,
  forgetting/salience tuning, ambient-tick economy.

### Holographic Parole Agents — design banked (user, 2026-07-10). 📋 UNBUILT (no issue)

The Constabulary lobby's public face (lobby #4936): the automaton era
ends with PROJECTED agents.

* **Seats 4 → 3**; each remaining seat gets a **PROJECTOR** — a
  physical object, **hackable** (decking seam) and **vandalizable**
  (damage seam). Break the projector, kill the service.
* **SITTING in a seat auto-boots a holographic LLM parole agent
  assigned to the sitter; leaving the seat kills it.** Sit-triggered
  engagement replaces automaton logic entirely — dynamic on/off for
  free, no idle brains burning tokens at an empty bench.
* **Register:** civic — fines, parole check-ins, civic requests. The
  HOLOGRAPHIC_MERCHANT precedent covers projected-being presentation.
* **Lane (2026-07-11 doctrine):** the CIVIC/fast lane is the natural
  fit — clerk-register, single-purpose dialogue at sub-second tempo,
  structural fallback lines, guardrail-compatible content. The GM lane
  stays reserved for characters with souls; a parole hologram is a
  form with a face.
* The broken automaton **#4951 stays** as set-dressing fossil (its
  OUT OF ORDER grille clicks on).

---

## 15 · Not decided

1. **Latency budget number** — what p95 reads as "alive" vs "laggy" for a
   directly-addressed NPC? Drives quant/model-size trade. *Measure on both
   minis.*
2. **Initiative cadence/budget number** for crafted/active NPCs (§13, item 3).
3. **Persona card** — the card schema/format and the auto-generator, and the
   consolidation rules that write experience back into mutable state (§13,
   item 4).
4. **Memory forgetting policy** — concrete salience/decay/summarisation rules
   (left as methodology in §6; needs a first cut to tune in play). The first
   cut is in §6.
5. **Multi-player scenes** — when several PCs engage one NPC, whose perception/
   turn ordering wins? (v1 may simply serialise by arrival/initiative.)
6. **GM-authored events** — explicitly deferred (§0.1). When/if the storyteller
   graduates from puppeting NPCs to *directing scenes*, that is a separate spec
   with its own authority questions.

---

## Appendix A · Gelatinous bindings (concrete hooks)

*The engine-agnostic method is §0–§9, apart from their "In this game"
paragraphs; this appendix holds the real seams the adapters bind to.*

- **Perception inlet.** NPCs perceive speech through
  `Character.at_msg_receive(text, from_obj, **kwargs)` — see
  `typeclasses/llm_npc.py` (`LLMNpcMixin.at_msg_receive` → reacts to
  addressed/overheard speech, offering it to the post through
  `_handle_directed_speech` before `_classify_speech` decides whether the LLM
  answers). The Perception adapter generalises this to feed the GM queue,
  applying the identity/voice gating below.
- **Action outlet.** NPCs act via `obj.execute_cmd("say …")` /
  `execute_cmd("attack …")` (`typeclasses/llm_npc.py`, `world/bar.py`,
  `commands/CmdThrow.py`). The Action adapter routes approved intents here —
  driving the NPC through the same cmdset a player uses, so
  combat/medical/movement/economy apply unchanged.
- **Speech backbone.** `world/speech.py`
  (`broadcast_speech`, `render_speech_line`, `speech_payload`,
  `visible_voice_flavor`) renders speech per-observer with voice/hearing/identity
  gating — the path `say`/`to`/pose already share. `speech` intents render through
  it for free.
- **Identity-gated perception.** `world/identity.py` (`get_apparent_uid`,
  `get_apparent_gender`, recognition lookups) and `world/voice.py`
  (`get_apparent_voice_uid`, `remember_voice`) describe actors *as perceived*.
  The Perception adapter uses these so the GM sees "a tall woman" / a known name /
  a recognised voice — never the raw object.
- **Structured memory.** `Character.recognition_memory`
  (`typeclasses/characters.py`, AttributeProperty, `category="identity"`) and the
  parallel voice memory are the authoritative relationship store the Memory
  adapter's *exact* tier builds on; the vector store adds the episodic tier. This
  is the same `recognition_memory → vector index` read-through model sketched in
  `IDENTITY_RECOGNITION_SPEC.md` §indexing (where LLM synthesis was explicitly
  deferred — this spec is that deferred layer).
- **Governance interlocks.** The consent gate is
  `specs/TRUST_AND_CONSENT_SPEC.md` (third-party actions on
  awake/able-to-resist targets need consent; unconscious/restrained/dead are
  free actions — exactly the rule §5.4.3 enforces for NPCs). Audit logging can
  reuse the combat-audit sink pattern (`world/combat/debug.py`).
- **World snapshot.** For richer ambient awareness later, the **World State
  Intelligence System** (`proposals/WORLD_STATE_INTELLIGENCE_SYSTEM_SPEC.md`,
  #303) is the natural source for colony-level context in §5.2.4 — out of scope
  for v1, noted so the snapshot assembler isn't designed into a corner.

## Appendix B · Model candidate notes

See §4.2. Candidates are tracked as a *living shortlist*, not a decision — all
sourced as `mlx-community` 4-bit quants, scored with the §4.1 rubric on the
target Mac mini, and bound behind the §9 Model adapter so swapping is a config
change, not a code change. Re-evaluate every release cycle; uncensored
creative-writing tunes move fast.

## Related documents

- `specs/TRUST_AND_CONSENT_SPEC.md` — the consent gate.
- `IDENTITY_RECOGNITION_SPEC.md` — §embedding, §indexing.
- `NPC_NEEDS_AND_GOALS_SPEC` — the two-brain law (Principle 8).
- `NPC_MEMORY_AND_IDENTITY_SPEC` — §5b (memory erase), §8 (identity & posing).
- `NPC_PLATFORM_SPEC` — criterion 10 (`feel` retirement).
- `EMOTE_POSE_SPEC.md` — second-person carve-out.
- `proposals/WORLD_STATE_INTELLIGENCE_SYSTEM_SPEC.md` (#303).
- [[reference-gelatinous-llm-model-candidates]] — model/format specifics and tuning lessons.
