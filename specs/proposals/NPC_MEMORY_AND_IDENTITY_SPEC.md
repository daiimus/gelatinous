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

## 3 · Affective state is itself memory

How an NPC **feels** about a person — trust, suspicion, fondness, irritation,
amusement — is a first-class, recalled memory dimension that evolves with the
pattern of interaction and the claim-history. It is the lever that turns
identity tracking into character.

The response to a detected inconsistency is **not** a fixed rule — it's the
NPC's personality reading its own affective state:

- **Discreet** — clocks the third alias this month, says nothing, files it.
- **Fed up** — tired of your bullshit; gets cold, cuts you off, names the game.
- **Witty** — *"Which one are we using tonight, sugar?"*

The classical/tactical layer may gate hard reactions (a fed-up bouncer refusing
service); the *expression* is the LLM's. This is where Memory meets
`TRUST_AND_CONSENT_SPEC` — trust is the accumulated affective state, and many
third-party actions should consult it.

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

**Now (shippable on the existing Phase 2 plumbing):**
1. Re-key `llm_memories` from `#{patron.id}` → `apparent_uid`.
2. A `remember`/nickname **tool** so an NPC spontaneously coins or records a
   name through the real recognition mechanism.
3. **Claim-history** (§2) + a coarse **affective/trust** field (§3) in the
   memory record / a per-identity summary, surfaced into the MEMORY block.
4. Personality-driven inconsistency response — prompt/charter guidance, no new
   gate.

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
