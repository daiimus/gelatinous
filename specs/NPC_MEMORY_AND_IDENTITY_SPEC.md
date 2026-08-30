# NPC Memory & Identity Spec

> **Status:** ✅ **SHIPPED & LIVE** — verified against code 2026-08-02: `world/llm/memory.py` (embedding records, cosine similarity, salience decay), tests in `world/tests/test_llm_memory.py`.

> **Status: 🟡 §8 CORE SHIPPED & LIVE; affordance roadmap ahead (§6).** The full
> "remember people" loop runs (§8 COMPLETE): episodic memory re-keyed on
> `apparent_uid`, the `remember`/`feel` tools, per-identity `db.llm_dossiers`
> (name-history + valence, GM-readable + LLM-surfaced), ambient action-awareness.
> Built on the shipped Phase 2 memory plumbing (`world/llm/memory.py`, the sidecar
> embedder, `LLMNpcMixin` recall/write). The decided model — memory hangs on the
> **identity-signature spine**, names are **unverifiable claims**, naming is a
> **creative, trust-laden act** — is realised; the affordance roadmap (§6: photos,
> cyberbrains, NPC↔NPC gossip, lore namespace) is the forward part.
> **OPERATIONAL NOTE (2026-07-16→20): shipped ≠ exercised.** The §8 plumbing was
> live but DORMANT in play — the `remember`/`feel` tools fired ~zero because a 12B
> won't invoke a tool it's only *told* about in the tool list. DEMONSTRATING them
> in each archetype's few-shot (#1236/#1237) lit the layer up (bartender first,
> then companion/merchant/security; companion spot-bench confirmed `remember` then
> fired on the right cue). See the `LLM_GAMEMASTER_SPEC` tool-reliability note.
> Ties into `IDENTITY_RECOGNITION_SPEC`, `TRUST_AND_CONSENT_SPEC` ("SUPER
> IMPORTANT"), the forensics layer, and the cyberware system.

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

### 2b · A verified name requires PROOF (owner ruling 2026-08-29)

There is no way for an NPC to verify a name **in speech**, so everything spoken
is a claim — including "call me Blade", which is a self-styled claim rather than
a name. Provenance, not the string, is what separates them:

| kind | authored by | verifiable |
|---|---|---|
| true identity | the world | `real_sleeve_uid` — ground truth, OOC validation |
| **verified name** | a document — ID, wanted record, paydata | ✅ **field does not exist yet** |
| given name | the subject, to you | ❌ claim; may be a lie |
| self-styled | the subject | ❌ claim, but *offered* ("call me Blade") |
| imposed | an observer | ❌ coinage ("Fat Tony") — the subject may hate it |

Self-styled and imposed are both aliases and behave oppositely, which is why
provenance has to be recorded rather than inferred: Blade wants Blade, and
nobody introduces themselves as Fat Tony.

**The target scenario** (owner, 2026-08-29): *show an NPC a picture of someone
they know as Billy who is actually Robert Paulson, ask about them, and have the
NPC tell you they go by Billy, recognise the document as an official source, and
recall what they know about the man.*

What that needs, and what already exists:

| piece | status |
|---|---|
| "they go by Billy" | ✅ `assigned_name` |
| linking Billy ⇄ Robert Paulson as one body | ✅ `linked_to`, `walk_linked_chain`, `get_linked_aliases` — already renders "Also known as:" |
| memories about him, surfaced on request | ✅ RAG memory scoped by subject uid |
| a document as an object (ID, wanted poster) | ❌ |
| **a way to SHOW something to someone** | ❌ no `show` command exists at all |
| reading proof → writing `verified_name` + linking | ❌ |

The identity-chain machinery — the expensive half, built for disguise and
unmasking — is the rail this runs on. What is missing is the front end.

**Address is a CHOICE, not a lookup.** Which of these an NPC uses out loud is
the NPC's decision, and the natural selector is opinion (§3): a warm NPC uses
the name you gave, a hostile one uses the ugly nickname to your face, a wary one
saves it for when you have left. That makes "Fat Tony" an insult the sim
generates rather than a string someone typed. Blocked on the §12 balance
prerequisite — opinion needs tuning against real play before anything gates on
it.

### 2c · The dossier is the file (#2408)

Owner, 2026-08-29: *"Inherently, it's part of the whole dossier system, right?
Everything is a file."* Yes — and that settles what `remember` **is**.

`remember` is not a naming command. It is the act of **writing to your
dossier**, and the dossier is the same object `DECKING_MATRIX` §2 already
names: *"A contact / dossier is a file (who knows whom; a face-to-name
link)."* Recognition memory and its attestations are two columns of one
record:

```
assigned_name   what I call them          — introduction, coinage, or my choice
attested[]      what VOUCHED for them     — {name, issuer, authority, protocol}
linked_to       which faces are one body  — the disguise chain
real_sleeve_uid ground truth              — OOC validation only
```

Three consequences, and they are why the framing matters:

* **`remember` must reach anything you can perceive.** A face, a document in
  your hand, one on the bar, one somebody is holding up. Those are all
  "commit this to my file", and requiring a different verb per case is the
  hazard the owner rejected. Hands only for other people — their pockets are
  not on display, and a search that reached them would turn `look` into a
  frisk.
* **A face known only by paper is a legitimate record.** `times_seen` stays 0
  and `first_seen` reads "a face on constabulary notice", so the file never
  claims a meeting that did not happen.
* **The file is an attack surface.** When the net layer lands, a decker reads
  or edits a dossier the same way they read a wanted record, and forgery
  attacks the **protocol** rather than the name. This is already the design:
  §2b keeps provenance per attestation precisely so a forged seal has
  something to be forged *against*.

Nothing here should grow a second store. If a future feature wants to
remember a place, an event or an item, it extends this record — because it is
all one file.

## 3 · Affective state is itself memory

How an NPC **feels** about a person — trust, suspicion, fondness, irritation —
is a first-class memory dimension. It is the lever that turns identity tracking
into character.

**DECISION REVERSED 2026-08-29 (#2388). Opinion is the ENGINE'S, not the
model's.** This section previously read: *"valence is an LLM-adjusted metric…
the model judges what a person does and nudges its valence accordingly."* That
is platform law 4 inverted — the model authoring a state the game stores and
reads back — and this section itself named the consequence: *"trust is the
accumulated affective state, and many third-party actions should consult it."*
A mechanic would have depended on a model's word choice.

**Opinion** is now the clamped, half-life-decayed sum of what a person actually
DID, derived on read, sharing one decay rule with mood (`world/souls/thoughts`,
`NPC_TRAITS_SPEC` §12):

```
opinion_of(soul, uid)   -> -1.0 .. +1.0    derived, never stored
opinion_band(value)     -> warm / friendly / neutral / wary / hostile
opinion_note(soul, uid) -> the strongest surviving REASON
```

The `feel` tool is **retired**. The WHO line hands the voice the band *and the
reason*, so an NPC narrates the grievance the engine actually holds instead of
inventing one.

**The original intent survives, by other means.** This section wanted
persona-weighted reactions — *"Sully shrugs off what makes Vesper cold."* That
is trait **repricing** (`NPC_TRAITS_SPEC`), applied to opinion rather than to
needs: a trait scales how far a given event moves the score. Not built; the
seam is `add_opinion`'s valence argument. See §12 there for the balance
prerequisite — producers get tuned against real play BEFORE any consumer gates
on the number.

The expression stays the model's, and the examples below still hold —
**discreet** files it silently, **fed up** cuts you off, **witty** asks which
one we're using tonight. The engine decides the state; the voice performs it.

**Load-bearing dependency (partly delivered).** Valence-on-behaviour needs the
NPC to perceive behaviour, not just speech. Combat now feeds it directly —
`react_to_attack` writes a `-0.60` wound against the attacker — and courtesy
feeds it from speech. Poses and other room events still do not.

## 4 · Naming is a spontaneous, creative act (nicknames)

> **AMENDED 2026-08-29 (#2390).** Naming was doing two jobs under one name and
> only the model could do either. They are split now:
>
> | | what it is | owner |
> |---|---|---|
> | "I'm Marcus", "call me Blade" | someone **told** you — clerical | the **ENGINE**, deterministically (`identity.parse_introduction`) |
> | "the Toe Guy", "tab dodger" | coined from observation — creative | the **LLM**, as below |
>
> With the LLM breaker off, NPCs still learn the names people give them. What
> is lost is the coinage, which is flavour rather than mechanic — platform
> criterion 10.
>
> **Primary vs list (owner ruling 2026-08-29).** `assigned_name` is the
> **primary** — the one name used for display, pose and search. The alias list
> keeps **everything**: setting a new primary shifts the old one down the list
> rather than discarding it. So an NPC who coined "the Toe Guy" and is later
> told "I'm Iver" calls you Iver and *still knows both*. This supersedes the
> "sticky nickname" wording below, which read as the nickname staying primary;
> what is sticky is the MEMORY, not the display slot. Eventually the whole list
> becomes visible through the remember/memory interface; for now only NPCs hold
> it.
>
> **Destination: a net-file.** The dossier is not staying an attribute.
> `DECKING_MATRIX` §2 already names it — *"A contact / dossier is a file (who
> knows whom; a face-to-name link)"* — a real game object a decker can read,
> copy or forge, where editing the file edits the world. **Do not build an
> intermediate home for it.** It currently lives on `db.llm_dossiers`, which is
> the wrong name for a general memory, and moving it anywhere short of the file
> layer is work that gets thrown away.
>
> **Still owed from §2:** the claim-history proper — *which* names, *how often*,
> *how recently* — and the inconsistency event when a known face offers a new
> name. Today the list is flat, deduped and capped at 8.


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

3. **§8.3 (#758)** — aliases memory (`db.llm_dossiers`: name-history + valence,
   GM-readable + LLM-surfaced) + the `[WHO]` block.
4. **§8.4 (#760)** — ambient action-awareness: NPCs observe room poses cheaply
   (no LLM) and consume them on the next reply (`[RECENTLY]` block). The
   observe-≠-react design keeps the single-threaded model from saturating.
5. **§8.5 (#762)** — behaviour-driven valence: the `feel` tool lets the LLM nudge
   its read from what a person *does*, persona-weighted; surfaces in `[WHO]`,
   consulted by `TRUST_AND_CONSENT`.

**✅ §8 COMPLETE & LIVE.** The full loop runs: witness behaviour → adjust
feeling → treat them accordingly next time, keyed on perceived identity, with
names coined or learned.

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
