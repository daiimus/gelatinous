# LLM Gamemaster Spec

> **Status:** 📋 Proposal — not implemented (tracking #705). A methodology for
> running a **local LLM as a storyteller / gamemaster** that puppets NPCs:
> dialogue, a bounded set of actions, real command use, and **per-NPC memory
> sustained through RAG**. This document is deliberately **implementation-light**.
> It hands an implementer the *contracts and hooks* — the agent loop, the
> adapter interfaces, the model-selection rubric, the governance interlocks —
> not a port of one codebase's topology. The single Gelatinous-specific binding
> lives in **Appendix A**; everything above it should transfer to any MUD with a
> command layer and a perception bus. Runtime target: **MLX on Apple Silicon**
> (a Mac mini), as a decoupled sidecar. Interlocks with the deferred
> **Trust/Consent** gate (`proposals/TRUST_AND_CONSENT_SPEC.md`) and the
> recognition-memory sketch in `IDENTITY_RECOGNITION_SPEC.md` §embedding.

---

## 0 · Purpose & framing

NPCs today are **scripted reactors**: a bartender hears speech addressed to it,
keyword-matches a menu, and fulfils (Appendix A). That ceiling is low — every
behaviour is hand-authored, every NPC is a vending machine with flavour text.

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

Explicitly **out of scope for v1** (noted in §11): GM-authored world events /
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
   stack (MLX, ChromaDB, Evennia); a reader should be able to swap any one.
7. **Fail safe, fail quiet.** Every failure mode — model down, timeout, malformed
   output, validation reject — degrades to the *current* scripted behaviour or to
   silence, never to a crash or a broken-character leak.

---

## 2 · Architecture overview

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
  keep them resident; pay the load cost (seconds to tens of seconds) at boot, not
  per turn. Requests are stateless against a warm model.
- **Bounded generation.** Cap `max_tokens` hard (NPC turns are short — a line of
  dialogue and a couple of intents, not an essay). Stream if the transport
  supports it so the actuator can begin as the first intent resolves.
- **A latency budget, declared.** Pick a target (e.g. *≤ 2.5 s p95 for a dialogue
  turn*) and design around missing it: the game must behave correctly when the
  sidecar is slow or absent (§8 — debounce, "is thinking" affordance, fallback).
- **Single in-flight generation per accelerator.** Unified-memory Macs do one
  generation well at a time; concurrency is a **queue**, not parallel CUDA
  streams (§8).

The game ↔ sidecar contract is JSON over local IPC: the game sends `{npc_id,
event, world_snapshot}`; the sidecar returns `{intents[]}`. Neither side shares
process memory; the sidecar can be restarted, swapped, or moved to another box
without touching the game.

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

### 4.2 · Shortlist & recommendation (as of early 2026 — swappable)

Sweet spot for a Mac mini is **12B–24B at 4-bit** (quality without blowing the
latency budget or memory). Candidates, all available as `mlx-community` quants:

- **Primary recommendation — a Mistral-Small-24B creative/RP fine-tune**
  (e.g. TheDrummer's *Cydonia* line or the *Magnum v4* 22B–27B series). These
  are explicitly tuned for uncensored roleplay/storytelling prose and follow
  structure adequately. At 4-bit they fit comfortably with room for context and
  the embedding model alongside.
- **Low-latency / smaller-RAM fallback — a 12B Nemo-class tune** (e.g.
  *Rocinante 12B* or *Magnum v4 12B*, Mistral-Nemo base). Noticeably faster and
  lighter; slightly less coherent over long context. Good for a 16 GB mini or
  when turn latency matters more than prose ceiling.
- **General uncensored baseline** — a *Dolphin*-tuned base, if RP tunes
  underperform on instruction-following in your tests; tuned more for compliance
  than prose, so expect flatter dialogue.

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

---

## 5 · The agent loop in detail

### 5.1 · Perceive — the inlet

The GM wakes for an NPC when that NPC *perceives something it might react to*.
Drive this off the **existing perception surface**, not a new omniscient feed:

- **Speech addressed to / overheard by** the NPC.
- **Arrivals/departures, poses, and emotes** in the NPC's location.
- **Combat and medical events** the NPC is party to or witness of.
- **Scheduled ticks** (idle behaviour, initiative to *act* unprompted) — rate-
  limited, off by default for background NPCs.

Each event is normalised to `{npc_id, kind, actor (as perceived), content,
location, timestamp}` and pushed to the queue. **Debounce**: collapse a burst
(an actor typing three lines) into one turn so the GM responds to the *situation*,
not each token. Perception is **identity-gated** at this stage (Principle 3) — the
`actor` is described as *this NPC* would perceive them (sdesc / known-name /
voice), never the raw object.

### 5.2 · Assemble — context

The prompt is composed, in priority order, to fit the context budget:

1. **GM charter** (shared system prompt — the rules of being a gamemaster).
2. **Persona card** — the NPC's durable identity: who they are, voice, manner,
   wants, boundaries, relationships, current goals. Authored once, stored with
   the NPC. This is the *mask*.
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

### 5.3 · Infer — structured intents out

The model returns a **structured list of intents**, not free text. A minimal
schema:

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

Parse defensively: malformed output → **discard the turn** (fail quiet, §1.7),
optionally one retry with a "return valid schema only" reminder. Never actuate
from a partial parse.

### 5.4 · Arbitrate — validate, gate, de-conflict

The single most important stage. The model **proposed**; the game now **disposes**.
In order:

1. **Schema & affordance check** — every action's verb is on the allow-list;
   args resolve to things the NPC can actually perceive/reach. Reject the rest.
2. **Capability gate** — can this NPC *actually* do this now? Drunk, wounded,
   restrained, disarmed — the **command layer already enforces this** (Principle
   2), so a rejected command simply fails as it would for a player. The arbiter's
   job is to not *narrate* success the world didn't grant.
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

### 5.5 · Actuate

Approved intents become real game effects through the **same paths a player's
input takes**:

- **Speech** → the speech backbone's broadcast (per-observer identity/voice/
  hearing rendering applies automatically).
- **Actions** → `execute_cmd` on the NPC object (Appendix A). The command runs
  through the normal cmdset, permissions, and system hooks — combat, movement,
  economy all behave exactly as for a player. If the command fails in-world, that
  *is* the outcome; the GM doesn't get to override it.

Because actuation is "the NPC types a command," there is **no parallel
world-mutation path** to keep in sync — the keystone payoff of Principle 2.

### 5.6 · Remember — write-back to RAG

After actuation, the turn is committed to the NPC's **own memory namespace**:

- Take the model's `memory` nominations (§5.3) plus a deterministic episodic
  record (who was present — as perceived —, what was said/done, outcome,
  timestamp, location).
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
  footprint/quality trade). Account for its memory in the §3 budget.
- **Identity-gated keys.** Memory is filed against the **apparent** identity the
  NPC perceived (the same apparent-UID machinery as recognition — Appendix A), so
  a disguised or unintroduced actor is remembered as they were *seen*, and
  recognition later can promote "the tall woman" to a name. This is what makes
  disguise, introduction, and reputation *mean* something to an NPC.
- **Forgetting & salience.** Cap per-NPC memory; decay or summarise low-salience
  episodes over time (salience from §5.3 + recency + emotional weight). Unbounded
  memory is both a retrieval-quality problem and a storage one. *Methodology, not
  a fixed policy — tune in play.*
- **Consistency & recovery.** Because the store is an index over authoritative
  records, it can be rebuilt from them on cold start, migration, or corruption.

---

## 7 · Governance & safety

The defining tension: **an uncensored model inside a governed world.** Resolve it
by separating two axes that are usually conflated:

- **Content latitude (model axis)** — we *want* a model that will write a grim,
  adult, violent setting in character without refusing or moralising. Refusals
  here are a **defect** (they break immersion and waste turns). This is why §4
  selects for uncensored creative tunes.
- **World authority (game axis)** — the model has **none**. It proposes intents;
  the game adjudicates every one (§5.4). No prompt jailbreak can make an NPC do
  something the **command layer and consent gate** don't permit, because the
  model never touches the world directly — it only emits intents that the arbiter
  filters and the command layer executes under normal rules.

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
  NPCs back to scripted/idle behaviour instantly.
- **Failure is safe and quiet** (Principle 7): sidecar down/slow/garbled → the
  NPC falls back to its current scripted behaviour or stays silent. The world
  never crashes or breaks character because the model did.

---

## 8 · Concurrency, latency & scale

- **One generation at a time per accelerator.** A unified-memory Mac does a
  single generation well; treat the sidecar as a **serial queue**, not a parallel
  pool. Order the queue by priority (a player addressing an NPC outranks idle
  ambient behaviour).
- **Debounce and coalesce** (§5.1): one turn per *situation*, not per line.
- **Asynchrony end to end.** The game fires a request and continues; when intents
  return, it actuates on the reactor thread. Nothing player-facing ever waits
  synchronously on the model.
- **Thinking affordance.** For a directly-addressed NPC, a brief "…" / busy beat
  covers generation latency diegetically and sets expectations.
- **Scale is turns/sec, bounded by the accelerator.** Plan NPC population and
  ambient-tick rates against *one* serial generator. Most NPCs should be **idle
  unless perceived** (event-driven), not constantly thinking. Background "life"
  is cheap scripted behaviour; the model is spent on *interaction*.
- **Horizontal headroom (later):** the sidecar boundary (§3) means a second box
  or accelerator can host more NPCs without touching the game — out of scope now,
  but the architecture doesn't foreclose it.

---

## 9 · Adapter interfaces (the contracts)

The reference build binds these to MLX + ChromaDB + Evennia. An implementer
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
   real commands/speech via the host's player-input path. (Gelatinous:
   `execute_cmd` + the speech backbone — Appendix A.)
5. **Safety/governance adapter** — *proposed intents → approved intents.* Owns
   affordance checks, the capability and **consent** gates, de-confliction, rate
   limits, the OOC guard, audit logging, and the kill switch (§5.4, §7).

The **agent loop (§2.1) is engine-agnostic**; only these five adapters know about
MLX, ChromaDB, or Evennia.

---

## 10 · Build phases

- **Phase 0 — sidecar & model.** Stand up the MLX server; load a shortlisted
  model warm; prove the latency budget on the actual Mac mini; run the §4.1
  rubric and pick a starting model. *Deliverable: `prompt → text` over local IPC,
  measured.*
- **Phase 1 — one NPC, dialogue only.** Bind Perception + Model + Action adapters
  for a single existing NPC (e.g. a bartender). No memory, no actions beyond
  speech. The GM hears, the GM speaks in character, through the real backbone.
  *Deliverable: a conversation that stays in persona, fails safe when the sidecar
  is off.*
- **Phase 2 — memory.** Add the Memory adapter: per-NPC RAG namespace, write-back,
  identity-gated retrieval, built on `recognition_memory`. *Deliverable: the NPC
  remembers a prior encounter across sessions.*
- **Phase 3 — bounded actions.** Add the Action affordance list + the full
  arbiter (§5.4) including the capability and **consent** gates. A small,
  allow-listed verb surface. *Deliverable: the NPC takes a real, governed action
  through a command.*
- **Phase 4 — many NPCs & de-confliction.** One GM, multiple personas, serialised
  turns, priority queue, isolation verified across namespaces.
- **Phase 5 — hardening.** Audit logging, kill switch, rate limits, forgetting/
  salience tuning, ambient-tick economy.

Each phase is independently useful and independently revertible; nothing after
Phase 1 changes the player-facing default if disabled.

---

## 11 · Open questions

1. **Final hardware spec** (Mac mini RAM) — fixes the §4 model-size envelope.
   Resolve before committing to a primary model.
2. **Latency budget number** — what p95 reads as "alive" vs "laggy" for a
   directly-addressed NPC? Drives quant/model-size trade.
3. **Autonomy ceiling for v1** — how broad is the initial action allow-list? Lean
   conservative (speech + emotes + serve + move) and widen with confidence.
4. **Idle/unprompted behaviour** — do background NPCs ever act *without* a
   perception trigger, and at what (expensive) cadence? Default off.
5. **Persona authoring pipeline** — how are persona cards written, stored, and
   versioned? Reuse of existing NPC description/identity fields vs. a new card.
6. **Memory forgetting policy** — concrete salience/decay/summarisation rules
   (left as methodology in §6; needs a first cut to tune in play).
7. **Multi-player scenes** — when several PCs engage one NPC, whose perception/
   turn ordering wins? (v1 may simply serialise by arrival/initiative.)
8. **GM-authored events** — explicitly deferred (§0.1). When/if the storyteller
   graduates from puppeting NPCs to *directing scenes*, that is a separate spec
   with its own authority questions.
9. **Cost/always-on** — is the sidecar always resident, or spun up on player
   presence? Affects power/thermals on a always-on Mac mini.

---

## Appendix A · Gelatinous bindings (concrete hooks)

*Everything above is engine-agnostic. This appendix is the only Gelatinous-
specific section — the real seams the adapters bind to.*

- **Perception inlet.** NPCs already perceive speech through
  `Character.at_msg_receive(text, from_obj, **kwargs)` — see the bartender in
  `typeclasses/bar.py` (`Bartender.at_msg_receive` → reacts to addressed/overheard
  speech). The Perception adapter generalises this to feed the GM queue, applying
  the identity/voice gating below.
- **Action outlet.** NPCs already act via `obj.execute_cmd("say …")` /
  `execute_cmd("attack …")` (`typeclasses/bar.py`, `commands/CmdThrow.py`). The
  Action adapter routes approved intents here — driving the NPC through the same
  cmdset a player uses, so combat/medical/movement/economy apply unchanged.
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
  `proposals/TRUST_AND_CONSENT_SPEC.md` (third-party actions on awake/able-to-
  resist targets need consent; unconscious/restrained/dead are free actions —
  exactly the rule §5.4.3 enforces for NPCs). Audit logging can reuse the
  combat-audit sink pattern (`world/combat/debug.py`).
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
