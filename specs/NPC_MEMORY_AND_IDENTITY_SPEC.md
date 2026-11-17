# NPC Memory & Identity Spec

> **Status:** ✅ **SHIPPED & LIVE** — verified against code 2026-08-02: `world/llm/memory.py` (embedding records, cosine similarity, salience decay), tests in `world/tests/test_llm_memory.py`.

> **Status: 🟡 §8 CORE SHIPPED & LIVE; affordance roadmap ahead (§6).** The full
> "remember people" loop runs (§8 COMPLETE): episodic memory re-keyed on
> `apparent_uid`, the `remember` tool (`feel` was retired by #2388), per-identity
> `db.llm_dossiers` (the names the NPC knows someone by, GM-readable +
> LLM-surfaced), the engine-derived read on a person (§3), ambient
> action-awareness.
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
- `_address_handle` hands the model the name this NPC assigned, else the
  clothing-free short sdesc (on the radio, the voice as this NPC knows it) — so
  the prompt's `speaker_name` is already identity-correct.

## 2 · Names are claims, not facts

There is (currently) **no way for an NPC to verify a PC's name.** So a name is a
*claim*, and memory tracks the **pattern of claims**, never "the name":

- Per apparent identity, the NPC records **which names have been claimed, how
  often, and how recently** — a small claim-history, not a single field.
  📋 UNBUILT (no issue): today the list is flat, deduped and capped at 8, with no
  counts and no times (§4).
- Consistency builds trust; a *new* name for an identity the NPC has named
  before is an **inconsistency event** — noticed or not by perceptiveness, and
  *responded to by personality* (see §3). 📋 UNBUILT (no issue).

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
via piercing), not a parallel store. As built it is a separate attribute,
`db.llm_dossiers`, keyed by the same apparent_uid; §4 says where it is meant to
end up.

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

> **SUPERSEDED 2026-08-30 (#2408), noted 2026-09-12.** The `verified name` row
> in the table above is out of date in a way that matters: `verified_name` was
> REJECTED as the wrong model, not merely unbuilt. A document does not prove a
> true name — it ATTESTS one on an issuer's authority, and that name may
> legitimately be an alias. The live `CLUB_CARD` prototype is exactly that case:
> a Helix Lounge membership card at `commercial` authority whose own desc says
> the name on it "is not necessarily the one on anybody's papers"
> (`CLUB_CARD` in `world/prototypes.py`). What shipped is a per-observer
> `attested[]` column on the recognition entry — `{name, issuer, authority,
> protocol, verified}` — written by `world.identity.attest`, with
> `official_name()` as a QUERY over authority AND protocol. A `verified_name`
> property of a person "would collapse the disguise layer the moment it
> existed" (`attest`'s docstring), and `world/tests/test_documents.py` pins two
> observers holding different, equally honest records of one face
> (`test_two_observers_can_hold_different_records`).

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

> **UPDATE 2026-09-12: the PLAYER front end SHIPPED 2026-08-30 (#2408 / PR
> #2409).** Three of the ❌ rows above are stale:
>
> | row | today |
> |---|---|
> | a document as an object | ✅ `typeclasses.items.Document` (`typeclasses/items.py`) + `SLEEVE_ID` / `COLONY_ID` / `WANTED_NOTICE` / `CLUB_CARD` prototypes (`world/prototypes.py`) |
> | a way to SHOW something | ✅ as a CAPABILITY, though there is still no `show` verb and by design never will be — the owner rejected it; READING is the mechanic (`Document.return_appearance`, `typeclasses/items.py`), and `remember <papers>` reaches your inventory, the room, and other people's HANDS ONLY (`CmdRemember._find_document`, `commands/CmdCharacter.py` → `world.search.held_by_others`, `world/search.py`) |
> | reading proof → writing + linking | ✅ `identity.attest` (`world/identity.py`) writes `attested[]`; `identity._link_by_papers` (`world/identity.py`) links two faces carrying matching VERIFIED COLONY-tier papers. No `verified_name` field — see the note above |
>
> Also stale, in the row above those: `walk_linked_chain` has **no production
> caller left** — only tests (`world/identity.py`). The live walk is
> `linked_family`, which `get_linked_aliases` adopted in #2651 so
> "Also known as" reads the same from either face. That row's ✅ still stands;
> one of the three functions it names no longer participates.
>
> **The NPC-FACING read has been built since this note.** The NPC `look` tool
> takes a target (#3370, `LLMNpcMixin._look_at`): a person in the room, or a
> thing in the room or carried by the person it is talking to or by itself.
> Reading a document writes what it vouches for onto a face the NPC already
> has a recognition entry for (`Document.return_appearance` →
> `world.identity.attest`), and the WHO line names the papers that vouch for
> the person in front of it (`_relationship_line`, #3371). The Billy / Robert
> Paulson scenario is still not fully playable, for two reasons. Handing papers
> to an NPC reaches `world.service.receive`, whose only registered `on_receive`
> hook is the butcher's (`world/shop/service.py`). And recall is scoped to the
> person the NPC is talking to, so it cannot bring up what it knows about the
> person in the picture. The PC half is complete: `recall` renders `Papers:`
> rows (`commands/CmdCharacter.py`).

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
  and the first-encounter description reads "a face on <the document>", so the
  file never claims a meeting that did not happen.
* **The file is an attack surface.** When the net layer lands, a decker reads
  or edits a dossier the same way they read a wanted record, and forgery
  attacks the **protocol** rather than the name. This is already the design:
  §2b keeps provenance per attestation precisely so a forged seal has
  something to be forged *against*.

Nothing here should grow a second store. If a future feature wants to
remember a place, an event or an item, it extends this record — because it is
all one file.

> **STATUS 2026-09-12: §2c SHIPPED as designed, 2026-08-30 (#2408 / PR #2409,
> commit `a6d544f8`).** The `attested[]` column exists on the recognition entry
> exactly as drawn above — `{name, issuer, authority, protocol}` plus a
> `verified` flag — written by `world.identity.attest` and ranked by
> `attestations()`. The
> constraint in the paragraph above held: no second store was grown, and
> `IDENTITY_RECOGNITION_SPEC` now documents the column on the recognition entry
> and points back to §2b for its meaning. `remember` does reach papers
> in your inventory, on the floor, and in another person's HANDS ONLY
> (`CmdRemember._find_document` → `world.search.held_by_others` — hands-only
> on purpose:
> "a search that reached those would quietly turn `look` into a frisk"). The
> attack-surface half still waits on the net layer, as written; the forgery
> design it anticipates is drafted in
> `specs/proposals/BACKUPS_AND_MEMORY_FORGERY_SPEC.md`.

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

An NPC that forgets somebody loses its read on them with the rest (§5b, #3851).

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
  *(Superseded 2026-08-29, #2390: the name set last becomes primary and the old
  one moves down the alias list; see the amendment at the top of §4.)*
- **Communicable by PCs**, not auto-shared between NPCs (see §6 gossip).

## 5 · Disguise / recognition interplay

When an NPC **pierces** a disguise (recognizes the voice/tells under a new face —
existing `attempt_*_pierce` machinery), it connects two `apparent_uid`s as one
underlying person. The **name discrepancy across those identities becomes a
character beat**: *"You were someone else yesterday."* Whether the NPC
**acknowledges** it (calls it out vs. keeps its counsel) is §3 personality. The
merge of episodic + claim-history across the connected identities is the
mechanical payoff.

> **Shipped 2026-09-13 (#3371, owner ruling option A).** The WHO line now reads the whole `linked_family`: aliases are the UNION across every connected face, opinion is the SUM of the decayed opinion held against each face (`souls.thoughts.opinion_over`) -- connecting two faces is a full merge, so a grudge earned as face A reads on face B and cannot be laundered by changing faces -- and papers something vouched for (`identity.attestations`) are surfaced, the NPC-side twin of `recall`'s `Papers:` rows. Memory retrieval had followed the chain since #2410; this was the other half.

## 5b · Forgetting

Owner ruling, 2026-11-15 (#3841): *"This should be identical to what a player loses. Their behavior is ideally identical to avoid cheating/hacking."*

`forget` is a real erase of one look from one observer (`IDENTITY_RECOGNITION_SPEC.md`, the `forget` command). An NPC is an observer like any other, so the recognition entry, every pointer to it, the voice named with it and the see-throughs won through it go for an NPC as they do for a player. An NPC also keeps records of its own, and each of them is put back in front of the model on the next turn. They go at the same door, `world.identity.erase_look`, which tells the observer which looks and which voices have just left its memory (`at_looks_erased`):

| What the NPC wrote down | Where | How the model was handed it |
|---|---|---|
| the names it knew them by | `db.llm_dossiers[uid]` | the WHO line: "you know them as ..." |
| what was said between them | `db.llm_memories` | the MEMORY block |
| the turns of the conversation | `ndb.llm_history` | the recent turns |
| its read on them, with the reason | `db.soul_opinions[uid]` | the WHO line: "your read on them: wary (because they put hands on me)" |

A record goes for either of two reasons:

- **It is filed under a forgotten look or voice** (its `subject`). A voice on the air is filed as `voice:<uid>`; when a voice entry goes with the look it was named with, what was filed under that voice goes too.
- **It was written under a forgotten name** (its `named_by`). The text of a memory and of a turn calls the speaker by the name the NPC had for them, and that name is not always the name of the look they are filed under: a look the NPC watched arrive answers to the name of the one it came from, and a disguised voice the NPC places answers to the name of the natural one. So each memory and each turn records the entry its name was read from, worked out together with the name and before the model is called. An NPC that served a masked figure as "Moth", later gave that figure a name of its own and then forgot Moth, loses what it wrote down while it called them Moth, and keeps what it wrote down after.

**The read on a person** went in by a ruling of its own. Owner, 2026-11-16 (#3851), to the recommendation that the read goes and the general mood stays: *"I concur with your recommendation."* The read is the entries of what the person did, each with its reason, filed under the look they wore (`world.souls.thoughts`, §3). It carries no name, so the first reason is the only one that applies to it: it goes when the look it is filed under was erased (`thoughts.forget_opinions`). An NPC that was still told "because they put hands on me" had not forgotten them.

This is a second road past the rule in §5 that a grudge cannot be shed by changing faces (#3371). A change of face does not shed it; a memory wipe does. That cost was named when the ruling was asked for.

**A look the NPC knew through the forgotten name** (#3859). An NPC that knows a person can come to hold records about a disguised look of that person in three ways. The owner was shown all three, with an NPC that is hit by the masked figure and later made to forget the person, and asked whether the second should end as the first does and the third be left. Owner, 2026-11-16: *"Yeah, your assessment is solid."*

| How the NPC knows the masked look | After it forgets the person |
|---|---|
| It watched the mask go on. The look has an unnamed entry that answers to the person's name. | The entry goes with the name (#3825), unless another name the NPC holds still reaches it, and everything filed under the look goes with it. |
| It saw through the mask. The look has no entry, only a won see-through. | The see-through goes with the name, and the look is reported to the NPC as forgotten: everything filed under it goes, as in the row above. |
| It gave the masked look a name of its own. | The look stays, and so does the NPC's read on it, whenever it was earned. What the NPC wrote down while it still called the look by the first name goes, as above; the rest of what is filed under the look stays. To clear it, the NPC forgets that name as well. |

The second row covers everything filed under the look, including what the masked figure did before the NPC saw through it. That was named when the ruling was asked for.

One thing at the edge of the second row:

- *The body the see-through was made on no longer exists.* A see-through is kept per body object, and one whose object has been deleted can no longer be read: nothing shows the NPC that name for that look. So such a look was a stranger's before the forget, and is treated as one: what is filed under it stays. If the NPC sees through the same look again on another body, that is a new see-through, and it goes as in the table.

**A voice the NPC placed** (#3861) follows the same rule. A person can sound different on the air than the voice the NPC named: they changed it with `@voice`, or use a voice modulator. The NPC has no voice entry for the changed voice. If it places the voice as theirs, what it hears from that voice on the air from then on is written under their name and goes with the name, by the second reason above. What it had filed under that voice before it placed it carries no name, and used to stay. The owner was shown both rows and asked whether the second should go too, as it does for a mask. Owner, 2026-11-16: *"You recommendation is fine."* So a voice the NPC holds no entry for, whose stored recognition goes with the name, is reported to it as forgotten, and everything filed under it goes.

What the code does around that, which the owner was not asked:

- A changed voice the NPC failed to place stays a stranger's, with its records. The NPC never connected it to the person, and a failed attempt stays failed (#3817).
- A voice that has an entry of its own in the NPC's voice memory is not reported, so what is filed under it stays, apart from what was written under the forgotten name. That is so for a voice the NPC has named, and also for a blank entry left by the `forget` of before #3825, as for a look.
- A recognition is stored per body object. One made on a body object that no longer exists is never erased, because the body cannot be looked up, and it no longer shows the NPC that name for the voice. It does not stop the voice being reported when the recognition made on the person's present body goes. A voice recognised only on a body that is gone is not reported: it was a stranger's before the forget, and what is filed under it stays, as for a look.

The blank entry and the body that is gone are the same two leftovers for a look and for a voice. Neither was asked of the owner; they are listed as open (#3863).

What that means in the cases that matter:

- **Only what was forgotten.** The looks are the ones `erase_look` reports: the named entry, the unnamed entries known only through it, and the looks with no entry that were known only by a see-through won through it. The voices are the voice entries that went with the look, and the voices with no entry that were only placed by one of those (#3861). A second name the NPC holds for the same person stays, with everything filed under it and written under it, its read on them included: the NPC connected the two (§5), and forgetting one name is not forgetting the other.
- **A thread is one conversation across looks.** It is filed under whichever look spoke last and holds the turns of every look the NPC had connected. Each turn records the look it was said under, so the forgotten look's turns leave a thread that stays, and the turns of a look that stays are kept out of a thread that goes. A thread that holds nothing to forget, and has nothing put back into it, is left as it is.
- **Somebody never named cannot be forgotten**, as for a player: `forget` forgets a name. What an NPC filed under a stranger's look stays. A look the NPC knew as somebody it had named is not a stranger's look, though it has no name of its own (the table above).
- **A reply still being made.** A reply takes time, and the record of it is written when it arrives. If the NPC is made to forget somebody while its reply to them is on its way, that reply is not written down under the name it has just lost: both writers check, as they write, that the entry the name was read from is still there. They also check that the look or voice the record is filed under has not been forgotten since the turn began. That second check needs no name, and it was added for the look an NPC saw through (#3859): the NPC calls that masked figure by a description, and the look is forgotten with the person it saw through to. It is not limited to that case. It asks what was forgotten, so it holds for every look and voice the forgetting took, which is the rule above that a record filed under a forgotten look goes (#3841): for one, a look that went with the name through an older entry joined to it by a link alone, which the NPC also calls by a description. Each forgetting is numbered and marks the looks and voices it took (`ndb.llm_forgotten`); a turn notes the number it began at.

What stays:

- **What is filed under nobody:** a mood (`db.soul_thoughts`) and the general memory a strong mood writes ("I remember: they put hands on me."). Part of everything a person does to an NPC goes into its general mood as well as into its read on them, and that part stays (#3851). So an NPC made to forget whoever attacked it is still shaken.
- **The lines waiting in the buffer of what the NPC has just seen happen.** They are already written out with names in them, as a player's screen is, and can show the forgotten name once more, in the NPC's next reply.
- **What the model itself said.** A reply that spoke the name while talking to somebody else is kept as it was said.
- **Records written before a record carried `named_by`**, unless they are filed under a forgotten look.
- **The conversation hold**, which is attention and not memory: an NPC made to forget the person it is talking to goes on listening to them until the hold runs out.

Nothing an NPC does today makes it forget. The model has a `remember` tool and no `forget` tool, and the command reaches an NPC only when staff type it for one. The door is there for the memory wipe §6 describes.

A resleeve is a separate road (`world/imprint.py`, `restore`). An NPC rebuilt after its death comes back from a backup taken 90 minutes (`GAP`) before it died. People it first met in that stretch come back as strangers, and its long-term memories, moods and reads on people from that stretch are not restored. The names it knew people by (`db.llm_dossiers`) are put back whole, so the WHO line can still say "you know them as ..." about a look the NPC no longer recognises (#3852).

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
- **LLM-GM loop:** recall = the MEMORY block; naming = the `remember` tool, routed
  to the real command (`LLMNpcMixin` `_handle_action_tool`); the read on a person
  is written by the engine, not by a tool (§3).

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
   > **CORRECTION 2026-09-12.** Both blocks ship UNBRACKETED — `WHO — …` and
   > `RECENTLY — …` (`world/llm/prompt.py`, `build_messages`). The brackets were
   > removed on purpose: a small RP model copied the inline `[gloss]` shape
   > straight into its dialogue (a bartender said "Lotta GANES [a nightrunner]
   > beneath the ice"), so an uppercase label plus an em-dash gives the same
   > structural boundary without a token pattern the model reproduces
   > (the comment above those blocks in `build_messages`). §8.3's `valence` half
   > is also inert now (#2388) — its live content is the ALIAS list (capped at 8,
   > `_note_alias`); the read on a person comes from `thoughts.opinion_over`.
   > The observe-≠-react mechanism itself is live: a pose arrives at
   > `at_msg_receive` and is buffered with NO LLM call (`_observe_action`), then
   > drained once by `_drain_actions` on the turn that consumes it. A wordless
   > pose aimed AT the NPC is buffered and also answered. The buffer also takes
   > arrivals and departures, radio traffic, the NPC's own refused commands,
   > acts an admin forced it to do, and combat beats (`world/llm/observation.py`).
   > It keeps the last six lines, each cut to 200 characters
   > (`LLM_ACTION_BUFFER`).
5. **§8.5 (#762, retired by #2388)** — the `feel` tool is gone. The NPC's read
   on a person is the engine's: `souls.thoughts.opinion_over`, handed to the
   voice in the WHO line (§3). Nothing consults it yet (`NPC_TRAITS_SPEC` §12).

**✅ §8 COMPLETE & LIVE.** The full loop runs: witness behaviour → adjust
feeling → treat them accordingly next time, keyed on perceived identity, with
names coined or learned.

> **QUALIFIED 2026-09-12.** §8 is complete as PLUMBING, but this sentence
> claims more than the code does, and it rests on item 5 above — which shipped
> as neither the `feel` tool nor a trust consumer (#2388). "Witness behaviour →
> adjust feeling" has exactly TWO producers in the whole colony: courtesy
> `+0.08` (`_note_courtesy`, `typeclasses/llm_npc.py`) and being attacked
> `-0.60` (`react_to_attack`, `world/director/civilians.py`). §3 above says the rest out loud —
> "Poses and other room events still do not" feed it — even though §8.4 ships
> the machinery that sees them (`_observe_action`,
> `typeclasses/llm_npc.py`). And "treat them accordingly" is NARRATION, not
> mechanic: nothing gates service, price, trust or access on the score, by
> deliberate ruling (`NPC_TRAITS_SPEC` §12, "Balance prerequisite — READ BEFORE
> WIRING A CONSUMER"). The loop closes through the voice — the WHO line hands
> the band and the reason to the model (`world/llm/prompt.py`, `build_messages`) — and that
> is the whole of it today.

**Later (roadmap, spec each deliberately):** photos as identity artifacts (§6); cyberbrain memory store (§6); NPC↔NPC
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
