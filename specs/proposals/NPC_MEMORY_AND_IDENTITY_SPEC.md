# NPC Memory & Identity Spec

> **Status: 🚧 DESIGN IN PROGRESS — NOT FOR IMPLEMENTATION.** Captures the
> decided design for how an LLM-driven NPC *remembers people*, building on the
> shipped Phase 2 memory plumbing (`world/llm/memory.py`, the sidecar embedder,
> `LLMNpcMixin` recall/write). It defines the model — memory hangs on the
> **identity-signature spine**, names are **unverifiable claims**, and naming is
> a **creative, trust-laden act** — plus the affordance roadmap (photos,
> cyberbrains, gossip). Build the §8 "now" slice deliberately; everything past
> it is roadmap. Ties into `IDENTITY_RECOGNITION_SPEC`, `TRUST_AND_CONSENT_SPEC`
> ("SUPER IMPORTANT"), the forensics layer, and the cyberware system.

## 0 · Purpose

Phase 2 gave NPCs episodic memory keyed by a placeholder (the interlocutor's
object id). That's wrong: in this world you **can't verify who anyone is**.
Identity is *presented* (sdesc, face, voice) and *claimed* (a name someone tells
you). A real memory model has to sit on perceived identity and treat a name as a
claim, not a fact — and that turns naming into character, trust, and comedy
rather than a database row. This spec defines that model so we build it on
purpose, not ad hoc.

## 1 · Memory rides the identity-signature spine

Recognition already exists for PCs and every Character (NPCs included):
`recognition_memory` (per-observer, keyed by **`apparent_uid`** — the perceived
identity, which shifts under disguise/mask/voice-modulator), `get_apparent_uid`,
`get_assigned_name`, disguise-piercing, and the auditory parallel `voice_memory`.

**Decision:** episodic memory (`db.llm_memories`) keys on **`apparent_uid`**, the
same spine recognition uses — not object id. Consequences fall out for free:

- A disguise (new apparent_uid) means the NPC sees a *stranger* and doesn't
  connect last week's tab. Realistic, and emergent.
- Recognition ("who is this?") and episodic memory ("what do I recall about
  them?") share one key. Two reads on one spine.
- `get_display_name(self)` already hands the NPC the name it has learned, else
  the sdesc — so the prompt's `speaker_name` is already identity-correct.

## 2 · Names are claims, not facts

There is (currently) **no way for an NPC to verify a PC's name.** So a name is a
*claim*, and memory tracks the **pattern of claims**, never "the name":

- Per apparent identity, the NPC records **which names have been claimed, how
  often, and how recently** — a small claim-history, not a single field.
- Consistency builds trust; a *new* name for an identity the NPC has named
  before is an **inconsistency event** — noticed or not by perceptiveness, and
  *responded to by personality* (see §3).

**Decision: an explicit "aliases memory" — the set of names the NPC knows a
person by** (its coined nickname + every name they've claimed), structured and
**dual-purpose**:

- **GM-usable.** Stored as real, human-readable data so a *human GM who puppets
  the NPC* (something we may never do, but must accommodate) can see at a glance
  "you know this person as X; they've also gone by Y, Z." Not a prompt-only
  artifact.
- **LLM-equipped.** The same aliases surface into the prompt so the model knows
  the full picture — what *it* calls them, and what they've *called themselves* —
  and can play the gap (§3).

The `remember` tool (§4) sets the *primary* name (the recognition `assigned_name`);
the aliases memory keeps the **history** around it. It lives alongside / extends
the recognition entry (which already keys on apparent_uid and links presentations
via piercing), not a parallel store.

## 3 · Affective state is itself memory

How an NPC **feels** about a person — trust, suspicion, fondness, irritation,
amusement — is a first-class, recalled memory dimension. It is the lever that
turns identity tracking into character. The recognition entry already carries a
`relationship_valence` (+ `notes`, `tags`, `recent_interactions`), so this has a
home — no new structure.

**Decision: valence is an LLM-adjusted metric driven by *experience*, not just
words.** The model has a perfectly good read on social behaviour — so it judges
what a person *does* and nudges its valence accordingly, exactly as a person
would. Does Bob pose about pissing on the bar? Kill someone in the room? Harass
the NPC? Tip well, defend the NPC, keep their word? Each shifts the read. The
**persona guides the weighting** — Sully shrugs off what makes Vesper cold; a
prim NPC and a gutter one score the same act differently.

The response to a detected inconsistency (§2) or a behaviour is **not** a fixed
rule — it's the NPC's personality reading its own valence:

- **Discreet** — clocks the third alias this month, says nothing, files it.
- **Fed up** — tired of your bullshit; gets cold, cuts you off, names the game.
- **Witty** — *"Which one are we using tonight, sugar?"*

The classical/tactical layer may gate hard reactions (a fed-up bouncer refusing
service); the *expression* is the LLM's. This is where Memory meets
`TRUST_AND_CONSENT_SPEC` — trust is the accumulated affective state, and many
third-party actions should consult it.

**⚠️ Load-bearing dependency:** valence-on-behaviour requires the NPC to
**perceive behaviour**. Today it reacts to *speech* only (`at_msg_receive` on the
speech payload) — a pure pose/emote/combat event isn't even noticed. So §8.3
depends on **ambient action-awareness**: the NPC observing room poses, emotes,
and combat events (attributed to an actor's apparent_uid), forming impressions
and updating valence. That's a feature in its own right (a slice before the
valence layer), and it rides the existing perception system + the speech
backbone's broadcast path.

## 4 · Naming is a spontaneous, creative act (nicknames)

A nickname is just a **self-authored `assigned_name`**, fed by a salient memory —
the recognition slot doesn't care if it holds "Jax" (claimed) or "the foot guy"
(coined). The loop:

1. The NPC accrues memories about an unnamed `apparent_uid`.
2. Those memories are already in the prompt (the MEMORY block). **Spontaneously**
   — the LLM's call, no threshold — the NPC may coin an epithet from them and
   call the **real `remember` mechanism as a tool** (per the real-commands
   mandate) to set `assigned_name`.
3. `get_display_name(self)` then hands *that NPC* the nickname; every new memory
   references it. Self-reinforcing.

Properties:

- **Private per NPC** (recognition_memory is per-observer) — same person, Sully's
  "the foot guy," Vesper's "the wandering eyes," Sable's "Jax." The *flavor* of
  the nickname is the personality talking. Free character.
- **Sticky** — a nickname is kept even after a real name is later claimed (truer,
  funnier). The claimed name is tracked separately (§2).
- **Communicable by PCs**, not auto-shared between NPCs (see §6 gossip).

## 5 · Disguise / recognition interplay

When an NPC **pierces** a disguise (recognizes the voice/tells under a new face —
existing `attempt_*_pierce` machinery), it connects two `apparent_uid`s as one
underlying person. The **name discrepancy across those identities becomes a
character beat**: *"You were someone else yesterday."* Whether the NPC
**acknowledges** it (calls it out vs. keeps its counsel) is §3 personality. The
merge of episodic + claim-history across the connected identities is the
mechanical payoff.

## 6 · Memory as substrate — affordance roadmap

Once memory hangs on the identity spine it stops being an NPC attribute and
becomes a **substrate with many I/O ports**, all keyed on the apparent-identity
signature:

- **Lived** — `llm_memories` from interaction (shipped).
- **Taught** — the `remember` tool (§4); or a **photo**: a photo *is* a captured
  identity signature, so showing one presents an `apparent_uid` the NPC matches
  against its recognition + episodic memory (*"Oh — the foot guy"*). Ties
  directly into the forensics layer, which already snapshots identity signatures
  (e.g. into blood pools).
- **Augmented — the cyber brain.** If memory lives "in" a neural-store augment,
  it becomes **hackable** (read/copy/wipe), **transferable** (stack-pull), and a
  **target** — damage the augment, damage the memory. Rides the cyberware system.
- **Gossip (future phase)** — PCs *and* NPCs are Characters, so NPC↔NPC sharing
  of labels/reads is possible later ("ask around about the foot guy"). Default
  off now; leave the seam.
- **Lore** — the shared read-only colony-knowledge namespace (per
  `LLM_GAMEMASTER_SPEC`), via the same RAG mechanism.

## 7 · Integration hooks (no new parallel systems)

- **Identity/recognition:** `recognition_memory` / `voice_memory`,
  `get_apparent_uid`, `get_assigned_name`, `get_display_name`, the `remember`
  command + `attempt_*_pierce`. Memory keys and the nickname tool route through
  these — never a second naming system.
- **Trust & consent:** affective state (§3) is the trust accumulator
  `TRUST_AND_CONSENT_SPEC` can consult; do not invent a separate one.
- **Forensics:** identity signatures already captured for blood pools are the
  same signatures a photo/recognition match would use.
- **Cyberware:** the memory store as an augment (cyberbrain) is a cyberware item
  with read/write/damage affordances.
- **LLM-GM loop:** recall = the MEMORY block; naming/trust updates = tools routed
  to real commands (`LLMNpcMixin` `_handle_action_tool`).

## 8 · Phasing

**✅ Shipped:**
1. **§8.1 (#753)** — re-key `llm_memories` on `apparent_uid` (disguise-aware).
2. **§8.2 (#755)** — the universal `remember` tool: NPCs coin/learn names through
   the real recognition mechanism, private per NPC.

**Next (still on existing plumbing):**
3. **Aliases memory** (§2) — the structured, GM-readable + LLM-surfaced history of
   names known for a person, extending the recognition entry; + a coarse
   **valence** read surfaced into the prompt. Personality-driven inconsistency
   response is charter guidance, no new gate.
4. **Ambient action-awareness** (the §3 ⚠️ dependency) — NPCs perceive room
   poses/emotes/combat (attributed to apparent_uid), not just speech. A feature
   in its own right and the prerequisite for behaviour-driven valence.
5. **Behaviour-driven valence** (§3) — the LLM nudges its read from what a person
   *does*, persona-weighted; surfaced back into the prompt + consulted by
   `TRUST_AND_CONSENT`.

**Later (roadmap, spec each deliberately):** disguise-merge of memory on piercing
(§5); photos as identity artifacts (§6); cyberbrain memory store (§6); NPC↔NPC
gossip (§6); lore namespace.

## 9 · Open questions

- Granularity of the affective field — a scalar trust + a few tags, or a richer
  model? (Start coarse.)
- Where the claim-history + affective summary live — on each episodic record, or
  a separate per-identity "dossier" the NPC keeps? (Leaning: a small per-identity
  dossier alongside the episodic list.)
- How perceptiveness gates *noticing* an inconsistency (stat/skill check vs.
  always-notice-but-personality-decides-acknowledgement).
- Salience for relational memory vs. episodic — does "how I feel" decay like a
  fact, or persist longer?
